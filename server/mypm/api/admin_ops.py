# -*- coding: utf-8 -*-
"""Admin/ops API endpoints.

Notes:
- This project no longer treats ./data as a git-managed repository.
- Backup/restore endpoints are kept as placeholders for future object storage integration.
"""

import os
import subprocess
from flask import Blueprint, jsonify, request, current_app

from ..domain.auth import require_admin
from ..storage.common import read_last_lines


bp = Blueprint('admin_ops', __name__)


def _get_deploy_service():
    """Get DeployService from app extensions."""
    return current_app.extensions.get('deploy_service')


def _get_root_dir():
    """Get project root directory."""
    return current_app.config.get('ROOT_DIR')


@bp.route('/backup', methods=['POST'])
def admin_backup_placeholder():
    """Backup placeholder (not implemented yet).

    Future: create a consistent SQLite snapshot and upload it to object storage.
    """
    ok, err = require_admin()
    if not ok:
        return err

    return jsonify({
        "success": False,
        "error": "Not implemented: backup is not wired yet",
        "hint": "Use: python scripts/sqlite_backup.py --db data/pm.db --out data/pm_backup.db",
    }), 501


@bp.route('/restore', methods=['POST'])
def admin_restore_placeholder():
    """Restore placeholder (not implemented yet)."""
    ok, err = require_admin()
    if not ok:
        return err

    return jsonify({
        "success": False,
        "error": "Not implemented: restore is not wired yet",
        "hint": "Stop service, replace data/pm.db with a known-good snapshot, then restart.",
    }), 501


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
