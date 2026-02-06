# -*- coding: utf-8 -*-
"""Statistics API endpoints."""

from flask import Blueprint, jsonify, current_app, request


bp = Blueprint('stats', __name__)


def _get_project_service():
    """Get ProjectService from app extensions."""
    return current_app.extensions.get('project_service')


def _get_token_usage_store():
    stores = current_app.extensions.get('stores', {})
    return stores.get('token_usage_store')


@bp.route('', methods=['GET'])
def get_statistics():
    """Get project statistics."""
    try:
        service = _get_project_service()
        stats = service.get_statistics()
        
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/tokens', methods=['GET'])
def get_token_statistics():
    """Get token/cost aggregation for web dashboards."""
    try:
        store = _get_token_usage_store()
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500

        data = store.aggregate(
            project_id=request.args.get('projectId'),
            agent_id=request.args.get('agentId'),
            workspace=request.args.get('workspace'),
            source=request.args.get('source'),
            since=request.args.get('since'),
            until=request.args.get('until'),
        )
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
