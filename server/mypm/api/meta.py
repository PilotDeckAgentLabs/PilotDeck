# -*- coding: utf-8 -*-
"""Meta/health API endpoints."""

import os
from datetime import datetime
from flask import Blueprint, jsonify, current_app

from ..domain.enums import PROJECT_STATUSES, PROJECT_PRIORITIES


bp = Blueprint('meta', __name__)


@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@bp.route('/meta', methods=['GET'])
def api_meta():
    """Lightweight, agent-friendly metadata about the service."""
    try:
        # Get project count
        store = current_app.extensions.get('projects_store')
        data = store.load()
        
        return jsonify({
            "success": True,
            "data": {
                "service": "MyProjectManager",
                "apiBase": "/api",
                "dataLastUpdated": data.get("lastUpdated"),
                "projectCount": len(data.get("projects", []) or []),
                "enums": {
                    "status": PROJECT_STATUSES,
                    "priority": PROJECT_PRIORITIES,
                },
                "auth": {
                    "agentTokenRequired": bool(os.environ.get('PM_AGENT_TOKEN', '').strip()),
                    "adminTokenRequired": bool(os.environ.get('PM_ADMIN_TOKEN', '').strip()),
                    "agentHeader": "X-PM-Agent-Token",
                    "adminHeader": "X-PM-Token",
                },
                "capabilities": {
                    "projects": True,
                    "stats": True,
                    "agentRuns": True,
                    "agentEvents": True,
                    "agentActions": True,
                    "projectsBatch": True,
                    "projectsPatch": True,
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
