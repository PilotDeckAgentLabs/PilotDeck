# -*- coding: utf-8 -*-
"""Agent profiles/capabilities and token usage APIs."""

from flask import Blueprint, jsonify, request, current_app


bp = Blueprint('agent_ops_api', __name__)


def _require_agent():
    fn = current_app.extensions.get('require_agent')
    if not fn:
        return True, None
    return fn()


def _stores():
    return current_app.extensions.get('stores', {})


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ('1', 'true', 'yes', 'on'):
        return True
    if s in ('0', 'false', 'no', 'off'):
        return False
    return None


@bp.route('/profiles', methods=['GET'])
def list_agent_profiles():
    try:
        enabled = _to_bool(request.args.get('enabled'))
        store = _stores().get('agent_profiles_store')
        items = store.list(enabled=enabled) if store else []
        return jsonify({"success": True, "data": items, "total": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/profiles', methods=['POST'])
def create_agent_profile():
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_profiles_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        body = request.get_json(silent=True) or {}
        item = store.create(body)
        return jsonify({"success": True, "data": item}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/profiles/<profile_id>', methods=['GET'])
def get_agent_profile(profile_id: str):
    try:
        store = _stores().get('agent_profiles_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        item = store.get(profile_id)
        if not item:
            return jsonify({"success": False, "error": f"Agent profile not found: {profile_id}"}), 404
        return jsonify({"success": True, "data": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/profiles/<profile_id>', methods=['PATCH'])
def patch_agent_profile(profile_id: str):
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_profiles_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        body = request.get_json(silent=True) or {}
        item = store.patch(profile_id, body)
        return jsonify({"success": True, "data": item})
    except KeyError:
        return jsonify({"success": False, "error": f"Agent profile not found: {profile_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/profiles/<profile_id>', methods=['DELETE'])
def delete_agent_profile(profile_id: str):
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_profiles_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        store.delete(profile_id)
        return jsonify({"success": True, "message": f"Agent profile deleted: {profile_id}"})
    except KeyError:
        return jsonify({"success": False, "error": f"Agent profile not found: {profile_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/capabilities', methods=['GET'])
def list_capabilities():
    try:
        enabled = _to_bool(request.args.get('enabled'))
        store = _stores().get('agent_capabilities_store')
        items = store.list(enabled=enabled) if store else []
        return jsonify({"success": True, "data": items, "total": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/capabilities', methods=['POST'])
def create_capability():
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_capabilities_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        body = request.get_json(silent=True) or {}
        item = store.create(body)
        return jsonify({"success": True, "data": item}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/capabilities/<capability_id>', methods=['GET'])
def get_capability(capability_id: str):
    try:
        store = _stores().get('agent_capabilities_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        item = store.get(capability_id)
        if not item:
            return jsonify({"success": False, "error": f"Capability not found: {capability_id}"}), 404
        return jsonify({"success": True, "data": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/capabilities/<capability_id>', methods=['PATCH'])
def patch_capability(capability_id: str):
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_capabilities_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        body = request.get_json(silent=True) or {}
        item = store.patch(capability_id, body)
        return jsonify({"success": True, "data": item})
    except KeyError:
        return jsonify({"success": False, "error": f"Capability not found: {capability_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/capabilities/<capability_id>', methods=['DELETE'])
def delete_capability(capability_id: str):
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('agent_capabilities_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        store.delete(capability_id)
        return jsonify({"success": True, "message": f"Capability deleted: {capability_id}"})
    except KeyError:
        return jsonify({"success": False, "error": f"Capability not found: {capability_id}"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/usage', methods=['POST'])
def ingest_usage():
    ok, err = _require_agent()
    if not ok:
        return err
    try:
        store = _stores().get('token_usage_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500

        body = request.get_json(silent=True) or {}
        records = body.get('records') if isinstance(body.get('records'), list) else [body]
        results = []
        created = 0
        for r in records:
            if not isinstance(r, dict):
                results.append({"success": False, "error": "record must be an object", "record": r})
                continue
            rec, was_created = store.ingest(r)
            results.append({"success": True, "created": was_created, "data": rec})
            if was_created:
                created += 1

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "received": len(records),
                "created": created,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/usage', methods=['GET'])
def list_usage():
    try:
        store = _stores().get('token_usage_store')
        if not store:
            return jsonify({"success": False, "error": "stores not configured"}), 500
        limit = request.args.get('limit')
        lim = 200
        if limit:
            try:
                lim = max(1, min(5000, int(limit)))
            except Exception:
                lim = 200

        items = store.list(
            project_id=request.args.get('projectId'),
            agent_id=request.args.get('agentId'),
            workspace=request.args.get('workspace'),
            source=request.args.get('source'),
            since=request.args.get('since'),
            until=request.args.get('until'),
            limit=lim,
        )
        return jsonify({"success": True, "data": items, "total": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
