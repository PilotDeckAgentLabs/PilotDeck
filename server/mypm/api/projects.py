# -*- coding: utf-8 -*-
"""Projects API endpoints."""

from flask import Blueprint, jsonify, request, current_app
from typing import Dict

from ..domain.errors import ProjectNotFoundError, ValidationError, ConcurrencyConflictError
from ..domain.auth import require_login_or_agent


bp = Blueprint('projects', __name__)


def _get_project_service():
    """Get ProjectService from app extensions."""
    return current_app.extensions.get('project_service')


@bp.route('', methods=['GET'])
@require_login_or_agent
def list_projects():
    """Get all projects (supports filtering)."""
    try:
        service = _get_project_service()
        
        # Query params
        status = request.args.get('status')
        priority = request.args.get('priority')
        category = request.args.get('category')
        
        projects, metadata = service.list_projects(
            status=status,
            priority=priority,
            category=category
        )
        
        return jsonify({
            "success": True,
            "data": projects,
            "total": metadata["total"],
            "lastUpdated": metadata.get("lastUpdated")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<project_id>', methods=['GET'])
@require_login_or_agent
def get_project(project_id: str):
    """Get single project by ID."""
    try:
        service = _get_project_service()
        project = service.get_project(project_id)
        
        return jsonify({
            "success": True,
            "data": project
        })
    except ProjectNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('', methods=['POST'])
@require_login_or_agent
def create_project():
    """Create new project."""
    try:
        service = _get_project_service()
        project_data = request.json or {}
        
        project = service.create_project(project_data)
        
        return jsonify({
            "success": True,
            "data": project,
            "message": "项目创建成功"
        }), 201
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<project_id>', methods=['PUT'])
@require_login_or_agent
def update_project(project_id: str):
    """Update project (full PUT semantics)."""
    try:
        service = _get_project_service()
        updates = request.json or {}
        
        project = service.update_project(project_id, updates)
        
        return jsonify({
            "success": True,
            "data": project,
            "message": "项目更新成功"
        })
    except ProjectNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<project_id>', methods=['PATCH'])
@require_login_or_agent
def patch_project(project_id: str):
    """Partial update for agents (PATCH semantics)."""
    try:
        service = _get_project_service()
        updates = request.get_json(silent=True) or {}
        
        # Extract optimistic lock parameter
        if_updated_at = updates.pop('ifUpdatedAt', None)
        
        project = service.patch_project(project_id, updates, if_updated_at=if_updated_at)
        
        return jsonify({
            "success": True,
            "data": project,
            "message": "项目更新成功"
        })
    except ProjectNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ConcurrencyConflictError as e:
        return jsonify({
            "success": False,
            "error": "Conflict: updatedAt mismatch",
            "data": {
                "message": str(e)
            }
        }), 409
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<project_id>', methods=['DELETE'])
@require_login_or_agent
def delete_project(project_id: str):
    """Delete project."""
    try:
        service = _get_project_service()
        service.delete_project(project_id)
        
        return jsonify({
            "success": True,
            "message": f"项目已删除: {project_id}"
        })
    except ProjectNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/reorder', methods=['POST'])
@require_login_or_agent
def reorder_projects():
    """Reorder projects by ID list (for drag-drop persistence)."""
    try:
        service = _get_project_service()
        body = request.json or {}
        ids = body.get('ids')
        
        if not isinstance(ids, list):
            return jsonify({
                "success": False,
                "error": "ids 必须是数组"
            }), 400
        
        projects = service.reorder_projects(ids)
        store = current_app.extensions.get('projects_store')
        last_updated = store.last_updated() if store else None
        
        return jsonify({
            "success": True,
            "data": projects,
            "total": len(projects),
            "lastUpdated": last_updated
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/batch', methods=['POST'])
@require_login_or_agent
def batch_update_projects():
    """Batch operations for agents.
    
    Body:
      {"ops": [{"id": "proj-...", "patch": {...}, "ifUpdatedAt": "...", "opId": "..."}, ...]}
    """
    try:
        service = _get_project_service()
        body = request.get_json(silent=True) or {}
        ops = body.get('ops')
        
        if not isinstance(ops, list):
            return jsonify({
                "success": False,
                "error": "ops must be an array",
            }), 400
        
        results, changed = service.batch_update(ops)
        store = current_app.extensions.get('projects_store')
        last_updated = store.last_updated() if store else None
        
        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "changed": changed,
                "lastUpdated": last_updated,
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
