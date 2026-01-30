# -*- coding: utf-8 -*-
"""Admin/ops API endpoints (deploy, push, pull)."""

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


@bp.route('/push', methods=['POST'])
def admin_push_to_github():
    """Push data/code to GitHub."""
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash)."
        }), 400

    # Flask 3.x: accessing request.json may raise 415 if Content-Type is not JSON.
    # This endpoint treats body as optional; be tolerant.
    body = request.get_json(silent=True) or {}
    mode = str(body.get('mode') or 'data-only').strip()
    if mode not in ('data-only', 'all'):
        return jsonify({
            "success": False,
            "error": "mode must be 'data-only' or 'all'"
        }), 400

    root_dir = _get_root_dir()
    script = os.path.join(root_dir, 'push_data_to_github.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "push_data_to_github.sh not found"
        }), 500

    cmd = ['bash', script]
    if mode == 'all':
        cmd.append('--all')

    try:
        # Ensure git can find config and SSH keys when run from systemd
        env = os.environ.copy()
        env.setdefault('HOME', os.path.expanduser('~'))
        env.setdefault('USER', os.getenv('USER', 'root'))
        
        p = subprocess.run(
            cmd,
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        
        output = (p.stdout or '').strip()
        
        if p.returncode != 0:
            # Extract meaningful error from output
            lines = output.split('\n')
            error_lines = [line for line in lines if '[ERROR]' in line or 'fatal:' in line or 'error:' in line]
            error_summary = error_lines[-1] if error_lines else f"push failed (exit {p.returncode})"
            
            return jsonify({
                "success": False,
                "error": error_summary,
                "output": output,
                "exitCode": p.returncode
            }), 500

        return jsonify({
            "success": True,
            "output": output
        })

    except subprocess.TimeoutExpired as e:
        output = (e.stdout or '').strip() if hasattr(e, 'stdout') else ''
        return jsonify({
            "success": False,
            "error": "push timed out (exceeded 180 seconds)",
            "output": output
        }), 504


@bp.route('/data/pull', methods=['POST'])
def admin_pull_data_repo():
    """Pull data repository updates."""
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash)."
        }), 400

    root_dir = _get_root_dir()
    script = os.path.join(root_dir, 'pull_data_repo.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "pull_data_repo.sh not found"
        }), 500

    try:
        # Ensure git can find config and SSH keys when run from systemd
        env = os.environ.copy()
        env.setdefault('HOME', os.path.expanduser('~'))
        env.setdefault('USER', os.getenv('USER', 'root'))
        
        p = subprocess.run(
            ['bash', script],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        
        output = (p.stdout or '').strip()
        
        if p.returncode != 0:
            # 2: dirty worktree, 4/5/6: misconfig
            http = 409 if p.returncode == 2 else 500
            
            # Extract meaningful error from output
            lines = output.split('\n')
            error_lines = [line for line in lines if '[ERROR]' in line or 'fatal:' in line or 'error:' in line]
            error_summary = error_lines[-1] if error_lines else f"pull data repo failed (exit {p.returncode})"
            
            return jsonify({
                "success": False,
                "error": error_summary,
                "output": output,
                "exitCode": p.returncode
            }), http

        return jsonify({
            "success": True,
            "output": output
        })

    except subprocess.TimeoutExpired as e:
        output = (e.stdout or '').strip() if hasattr(e, 'stdout') else ''
        return jsonify({
            "success": False,
            "error": "pull data repo timed out (exceeded 180 seconds)",
            "output": output
        }), 504


@bp.route('/merge-data-sync', methods=['POST'])
def admin_merge_data_sync_to_main():
    """Deprecated endpoint (data repo separated)."""
    ok, err = require_admin()
    if not ok:
        return err

    # Data is stored in a separate repository under ./data.
    # The legacy workflow (data-sync -> merge into main) no longer applies.
    return jsonify({
        "success": False,
        "error": "Deprecated: data repo is separated (./data). 'merge-data-sync' no longer applies.",
    }), 410


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
