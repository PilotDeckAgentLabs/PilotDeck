# -*- coding: utf-8 -*-
"""Statistics API endpoints."""

from flask import Blueprint, jsonify, current_app


bp = Blueprint('stats', __name__)


def _get_project_service():
    """Get ProjectService from app extensions."""
    return current_app.extensions.get('project_service')


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
