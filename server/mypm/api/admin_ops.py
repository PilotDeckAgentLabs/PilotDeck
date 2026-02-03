# -*- coding: utf-8 -*-
"""Admin/ops API endpoints.

Notes:
- This project no longer treats ./data as a git-managed repository.
- Backup/restore endpoints are kept as placeholders for future object storage integration.
"""

import os
import subprocess
import sqlite3
import tempfile
import threading
import shutil
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, send_file, after_this_request

from ..domain.auth import require_admin
from ..storage.common import read_last_lines


bp = Blueprint('admin_ops', __name__)


_restore_lock = threading.Lock()


def _get_deploy_service():
    """Get DeployService from app extensions."""
    return current_app.extensions.get('deploy_service')


def _get_root_dir():
    """Get project root directory."""
    return current_app.config.get('ROOT_DIR')


def _get_db_file() -> str:
    # Config is loaded via app.config.from_object(Config())
    # so keys like DB_FILE exist in current_app.config.
    return str(current_app.config.get('DB_FILE') or '').strip()


def _now_utc_compact() -> str:
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


def _sqlite_integrity_ok(path: str) -> bool:
    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            row = conn.execute('PRAGMA integrity_check;').fetchone()
            return bool(row and str(row[0]) == 'ok')
        finally:
            conn.close()
    except Exception:
        return False


@bp.route('/backup', methods=['GET'])
def admin_download_backup():
    """Export a consistent SQLite snapshot as a downloadable file."""
    ok, err = require_admin()
    if not ok:
        return err

    db_file = _get_db_file()
    if not db_file or not os.path.exists(db_file):
        return jsonify({
            "success": False,
            "error": "DB file not found",
            "data": {"dbFile": db_file},
        }), 404

    fd, tmp_path = tempfile.mkstemp(prefix='pm_backup_', suffix='.db')
    os.close(fd)

    @after_this_request
    def _cleanup(resp):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return resp

    try:
        src = sqlite3.connect(db_file, timeout=5.0)
        try:
            src.execute('PRAGMA foreign_keys=ON;')
            src.execute('PRAGMA busy_timeout=5000;')
            dst = sqlite3.connect(tmp_path, timeout=5.0)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to create backup: {str(e)}",
        }), 500

    name = f"pm_backup_{_now_utc_compact()}.db"
    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=name,
        mimetype='application/octet-stream',
        max_age=0,
    )


@bp.route('/restore', methods=['POST'])
def admin_restore_from_upload():
    """Restore database from an uploaded SQLite snapshot.

    Request: multipart/form-data with file field named "file".
    """
    ok, err = require_admin()
    if not ok:
        return err

    db_file = _get_db_file()
    if not db_file:
        return jsonify({
            "success": False,
            "error": "DB file path not configured",
        }), 500

    up = request.files.get('file')
    if not up:
        return jsonify({
            "success": False,
            "error": "Missing upload file (field name: file)",
        }), 400

    db_dir = os.path.dirname(db_file) or '.'
    os.makedirs(db_dir, exist_ok=True)

    # Save to a temp file in the SAME directory as db_file.
    # This allows atomic os.replace on Windows (cross-volume replace can fail).
    fd, tmp_path = tempfile.mkstemp(prefix='.pm_restore_', suffix='.db', dir=db_dir)
    os.close(fd)
    try:
        up.save(tmp_path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return jsonify({
            "success": False,
            "error": f"Failed to save upload: {str(e)}",
        }), 400

    try:
        if not _sqlite_integrity_ok(tmp_path):
            return jsonify({
                "success": False,
                "error": "Invalid SQLite backup (integrity_check failed)",
            }), 400

        with _restore_lock:
            # Best-effort: mark restore in progress so other requests can be blocked.
            current_app.extensions.setdefault('maintenance', {})
            current_app.extensions['maintenance']['restoring_db'] = True
            try:
                ts = _now_utc_compact()
                backup_old = f"{db_file}.bak.{ts}"
                if os.path.exists(db_file):
                    os.replace(db_file, backup_old)

                # Replace main db atomically.
                os.replace(tmp_path, db_file)

                # Remove sidecars if any.
                for side in (db_file + '-wal', db_file + '-shm'):
                    try:
                        if os.path.exists(side):
                            os.remove(side)
                    except Exception:
                        pass

                return jsonify({
                    "success": True,
                    "data": {
                        "dbFile": db_file,
                        "previousDbBackup": backup_old if os.path.exists(backup_old) else None,
                    }
                })
            finally:
                current_app.extensions['maintenance']['restoring_db'] = False
    finally:
        # tmp_path may have been moved into place via os.replace.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@bp.route('/deploy', methods=['POST'])
def admin_deploy_pull_restart():
    """Deploy: pull code, install deps, restart service."""
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash + systemctl/nohup)."
        }), 400

    root_dir = _get_root_dir()
    script = os.path.join(root_dir, 'deploy_pull_restart.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "deploy_pull_restart.sh not found"
        }), 500

    try:
        deploy_service = _get_deploy_service()
        result = deploy_service.start_deploy_job(script)
        
        return jsonify({
            "success": True,
            "jobId": result["jobId"],
            "unit": result.get("unit"),
            "pid": result.get("pid"),
            "method": result["method"],
            "logFile": "deploy_run.log",
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/deploy/log', methods=['GET'])
def admin_deploy_log():
    """Get deploy log tail."""
    ok, err = require_admin()
    if not ok:
        return err

    deploy_service = _get_deploy_service()
    lines = read_last_lines(deploy_service.log_file, max_lines=240)
    
    return jsonify({
        "success": True,
        "lines": lines
    })


@bp.route('/deploy/status', methods=['GET'])
def admin_deploy_status():
    """Get deploy job status."""
    ok, err = require_admin()
    if not ok:
        return err

    deploy_service = _get_deploy_service()
    status = deploy_service.get_deploy_status()
    
    return jsonify({
        'success': True,
        'data': status
    })
