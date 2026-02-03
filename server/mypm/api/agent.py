# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint('agent_api', __name__)


def _require_agent():
    fn = current_app.extensions.get('require_agent')
    if not fn:
        return True, None
    return fn()


def _stores():
    return current_app.extensions.get('stores', {})


def _project_service():
    return current_app.extensions.get('project_service')


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _clamp_int(v, lo: int, hi: int) -> int:
    try:
        iv = int(v)
    except Exception:
        iv = lo
    if iv < lo:
        return lo
    if iv > hi:
        return hi
    return iv


def _project_find_by_id(data: Dict, project_id: str) -> Optional[Dict]:
    for p in data.get('projects', []) or []:
        if isinstance(p, dict) and p.get('id') == project_id:
            return p
    return None


def _project_get_tags(project: Dict) -> List[str]:
    tags = project.get('tags')
    if not isinstance(tags, list):
        return []
    out = []
    for t in tags:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def _build_action_event(action_id: str, *, project_id: str, run_id: Optional[str], agent_id: Optional[str],
                        typ: str, level: str, title: str, message: str, data: Dict) -> Dict:
    now = datetime.now().isoformat()
    return {
        'id': action_id,
        'ts': now,
        'type': typ,
        'level': level,
        'projectId': project_id,
        'runId': run_id,
        'agentId': agent_id,
        'title': title,
        'message': message,
        'data': data,
    }


@bp.route('/actions', methods=['POST'])
def agent_actions():
    ok, err = _require_agent()
    if not ok:
        return err

    try:
        body = request.get_json(silent=True) or {}
        agent_id = body.get('agentId')
        run_id = body.get('runId')
        default_project_id = body.get('projectId')
        actions = body.get('actions')
        if not isinstance(actions, list) or not actions:
            return jsonify({"success": False, "error": "actions must be a non-empty array"}), 400

        stores = _stores()
        events_store = stores.get('agent_events_store')
        project_service = _project_service()
        if not events_store or not project_service:
            return jsonify({"success": False, "error": "stores not configured"}), 500

        changed = False
        results = []

        for a in actions:
            try:
                if not isinstance(a, dict):
                    raise ValueError('action must be an object')

                action_id = str(a.get('id') or '').strip()
                if not action_id:
                    action_id = f"act-{str(uuid.uuid4())[:8]}"

                existing = events_store.exists(action_id)
                if existing:
                    pid = existing.get('projectId') or (a.get('projectId') or default_project_id)
                    project = None
                    if pid:
                        try:
                            project = project_service.get_project(str(pid))
                        except Exception:
                            project = None
                    results.append({
                        "id": action_id,
                        "success": True,
                        "status": 200,
                        "projectId": pid,
                        "event": existing,
                        "project": project,
                        "message": "action exists",
                    })
                    continue

                project_id = a.get('projectId') or default_project_id
                if not project_id or not isinstance(project_id, str):
                    raise ValueError('projectId is required')

                try:
                    project = project_service.get_project(project_id)
                except Exception:
                    results.append({
                        "id": action_id,
                        "success": False,
                        "status": 404,
                        "projectId": project_id,
                        "error": f"项目未找到: {project_id}",
                    })
                    continue

                if_updated_at = a.get('ifUpdatedAt')
                if if_updated_at and str(project.get('updatedAt') or '') != str(if_updated_at):
                    results.append({
                        "id": action_id,
                        "success": False,
                        "status": 409,
                        "projectId": project_id,
                        "error": "Conflict: updatedAt mismatch",
                        "data": {
                            "expectedUpdatedAt": if_updated_at,
                            "actualUpdatedAt": project.get('updatedAt'),
                        }
                    })
                    continue

                action_type = str(a.get('type') or '').strip()
                params = a.get('params') if isinstance(a.get('params'), dict) else {}
                record_only = bool(a.get('recordOnly'))

                before = {
                    "status": project.get('status'),
                    "priority": project.get('priority'),
                    "progress": project.get('progress'),
                    "tags": _project_get_tags(project),
                }
                patch = {}
                event_message = ''

                if action_type == 'set_status':
                    status = str(params.get('status') or '').strip()
                    allowed = {"planning", "in-progress", "paused", "completed", "cancelled"}
                    if status not in allowed:
                        raise ValueError(f"invalid status: {status}")
                    if project.get('status') != status:
                        patch['status'] = status
                    event_message = f"set status -> {status}"
                elif action_type == 'set_priority':
                    pr = str(params.get('priority') or '').strip()
                    allowed = {"low", "medium", "high", "urgent"}
                    if pr not in allowed:
                        raise ValueError(f"invalid priority: {pr}")
                    if project.get('priority') != pr:
                        patch['priority'] = pr
                    event_message = f"set priority -> {pr}"
                elif action_type == 'set_progress':
                    nv = _clamp_int(params.get('progress'), 0, 100)
                    if int(project.get('progress') or 0) != nv:
                        patch['progress'] = nv
                    event_message = f"set progress -> {nv}%"
                elif action_type == 'bump_progress':
                    delta = params.get('delta')
                    try:
                        d = int(delta)
                    except Exception:
                        raise ValueError('delta must be an integer')
                    cur = int(project.get('progress') or 0)
                    nv = _clamp_int(cur + d, 0, 100)
                    if cur != nv:
                        patch['progress'] = nv
                    event_message = f"bump progress {d} -> {nv}%"
                elif action_type == 'append_note':
                    note = str(params.get('note') or '').strip()
                    if not note:
                        raise ValueError('note is required')
                    also_write = bool(params.get('alsoWriteToProjectNotes'))
                    if also_write:
                        cur_notes = str(project.get('notes') or '').rstrip()
                        prefix = datetime.now().strftime('%Y-%m-%d %H:%M')
                        who = str(agent_id or 'agent')
                        line = f"[{prefix}] ({who}) {note}"
                        patch['notes'] = (cur_notes + "\n" + line).lstrip() if cur_notes else line
                    event_message = note
                elif action_type == 'add_tag':
                    tag = str(params.get('tag') or '').strip()
                    if not tag:
                        raise ValueError('tag is required')
                    tags = _project_get_tags(project)
                    if tag not in tags:
                        tags.append(tag)
                        patch['tags'] = tags
                    event_message = f"add tag: {tag}"
                elif action_type == 'remove_tag':
                    tag = str(params.get('tag') or '').strip()
                    if not tag:
                        raise ValueError('tag is required')
                    tags = _project_get_tags(project)
                    if tag in tags:
                        tags = [t for t in tags if t != tag]
                        patch['tags'] = tags
                    event_message = f"remove tag: {tag}"
                else:
                    raise ValueError(f"unknown action type: {action_type}")

                after = {
                    "status": patch.get('status', project.get('status')),
                    "priority": patch.get('priority', project.get('priority')),
                    "progress": patch.get('progress', project.get('progress')),
                    "tags": patch.get('tags', _project_get_tags(project)),
                }

                if (not record_only) and patch:
                    try:
                        project = project_service.patch_project(project_id, patch, if_updated_at=if_updated_at)
                        changed = True
                    except Exception as e:
                        # Keep the existing API behavior for conflicts.
                        msg = str(e)
                        if 'mismatch' in msg or 'Conflict' in msg:
                            results.append({
                                "id": action_id,
                                "success": False,
                                "status": 409,
                                "projectId": project_id,
                                "error": "Conflict: updatedAt mismatch",
                                "data": {"message": msg}
                            })
                            continue
                        raise

                evt = _build_action_event(
                    action_id,
                    project_id=project_id,
                    run_id=run_id,
                    agent_id=agent_id,
                    typ=f"action.{action_type}",
                    level='info',
                    title=action_type,
                    message=event_message,
                    data={
                        "action": {
                            "type": action_type,
                            "params": params,
                            "recordOnly": record_only,
                            "ifUpdatedAt": if_updated_at,
                        },
                        "before": before,
                        "after": after,
                        "projectUpdatedAt": project.get('updatedAt'),
                    }
                )
                events_store.append(evt)

                results.append({
                    "id": action_id,
                    "success": True,
                    "status": 200,
                    "projectId": project_id,
                    "changed": bool((not record_only) and patch),
                    "project": project,
                    "event": evt,
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "status": 400,
                    "error": str(e),
                    "action": a,
                })

        if changed:
            projects_store.save(data)

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "changed": changed,
                "lastUpdated": getattr(stores.get('projects_store'), 'last_updated', lambda: None)(),
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/events', methods=['POST'])
def agent_create_event():
    ok, err = _require_agent()
    if not ok:
        return err

    stores = _stores()
    events_store = stores.get('agent_events_store')
    if not events_store:
        return jsonify({"success": False, "error": "stores not configured"}), 500

    try:
        body = request.get_json(silent=True) or {}
        event_id = str(body.get('id') or '').strip()
        if event_id:
            existing = events_store.exists(event_id)
            if existing:
                return jsonify({"success": True, "data": existing, "message": "event exists"})
        else:
            event_id = f"evt-{str(uuid.uuid4())[:8]}"

        now = datetime.now().isoformat()
        event = {
            "id": event_id,
            "ts": now,
            "type": str(body.get('type') or 'note').strip(),
            "level": str(body.get('level') or 'info').strip(),
            "projectId": body.get('projectId'),
            "runId": body.get('runId'),
            "agentId": body.get('agentId'),
            "title": body.get('title'),
            "message": body.get('message'),
            "data": body.get('data'),
        }
        events_store.append(event)
        return jsonify({"success": True, "data": event}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/events', methods=['GET'])
def agent_list_events():
    ok, err = _require_agent()
    if not ok:
        return err

    stores = _stores()
    events_store = stores.get('agent_events_store')
    if not events_store:
        return jsonify({"success": False, "error": "stores not configured"}), 500

    try:
        project_id = request.args.get('projectId')
        run_id = request.args.get('runId')
        agent_id = request.args.get('agentId')
        typ = request.args.get('type')
        since = request.args.get('since')
        limit = request.args.get('limit')

        since_dt = _parse_iso(str(since or '').strip())
        lim = 200
        if limit:
            try:
                lim = max(1, min(2000, int(limit)))
            except Exception:
                lim = 200

        events = events_store.list(
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            typ=typ,
            since_dt=since_dt,
            limit=lim,
        )

        return jsonify({"success": True, "data": events, "total": len(events)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# === Agent Runs Endpoints ===

@bp.route('/runs', methods=['POST'])
def agent_create_run():
    """Create new agent run (idempotent)."""
    ok, err = _require_agent()
    if not ok:
        return err

    try:
        from ..domain.errors import AgentRunNotFoundError
        agent_service = current_app.extensions.get('agent_service')
        
        body = request.get_json(silent=True) or {}
        run = agent_service.create_run(body)
        
        # Check if this was existing run (idempotency)
        message = "run exists" if run.get('createdAt') != run.get('updatedAt') else None
        
        return jsonify({
            "success": True,
            "data": run,
            "message": message
        }), 201 if not message else 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/runs', methods=['GET'])
def agent_list_runs():
    """List agent runs with filtering."""
    ok, err = _require_agent()
    if not ok:
        return err

    try:
        agent_service = current_app.extensions.get('agent_service')
        
        project_id = request.args.get('projectId')
        agent_id = request.args.get('agentId')
        status = request.args.get('status')
        limit = request.args.get('limit')
        offset = request.args.get('offset')

        lim = 50
        off = 0
        if limit:
            try:
                lim = max(1, min(500, int(limit)))
            except Exception:
                lim = 50
        if offset:
            try:
                off = max(0, int(offset))
            except Exception:
                off = 0

        runs, total = agent_service.list_runs(
            project_id=project_id,
            agent_id=agent_id,
            status=status,
            limit=lim,
            offset=off
        )

        return jsonify({
            "success": True,
            "data": runs,
            "total": total,
            "limit": lim,
            "offset": off,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/runs/<run_id>', methods=['GET'])
def agent_get_run(run_id: str):
    """Get single run by ID."""
    ok, err = _require_agent()
    if not ok:
        return err

    try:
        from ..domain.errors import AgentRunNotFoundError
        agent_service = current_app.extensions.get('agent_service')
        
        run = agent_service.get_run(run_id)
        return jsonify({"success": True, "data": run})
    
    except AgentRunNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/runs/<run_id>', methods=['PATCH'])
def agent_patch_run(run_id: str):
    """Update agent run (PATCH)."""
    ok, err = _require_agent()
    if not ok:
        return err

    try:
        from ..domain.errors import AgentRunNotFoundError
        agent_service = current_app.extensions.get('agent_service')
        
        patch = request.get_json(silent=True) or {}
        run = agent_service.patch_run(run_id, patch)
        
        return jsonify({"success": True, "data": run})
    
    except AgentRunNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
