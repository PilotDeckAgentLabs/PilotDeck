# -*- coding: utf-8 -*-
"""Domain models (data classes / type hints).

NOTE: Currently plain dicts are used throughout the codebase.
This module provides type aliases and normalization functions.
Future: migrate to Pydantic models when moving to FastAPI.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import uuid

from .enums import (
    PROJECT_STATUS_PLANNING,
    PROJECT_PRIORITY_MEDIUM,
    AGENT_RUN_STATUS_RUNNING,
    EVENT_LEVEL_INFO,
)


# Type aliases (until Pydantic migration)
Project = Dict[str, Any]
AgentRun = Dict[str, Any]
AgentEvent = Dict[str, Any]
AgentProfile = Dict[str, Any]
AgentCapability = Dict[str, Any]
TokenUsageRecord = Dict[str, Any]


def normalize_project(p: Any) -> Tuple[Project, bool]:
    """Normalize a single project record, returning (project, changed).
    
    Ensures all required fields exist with proper types and defaults.
    Backward compatible: missing fields are filled with defaults.
    """
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(p, dict):
        p = {}
        changed = True
    project: Project = dict(p)

    # Identity
    pid = project.get('id')
    if not isinstance(pid, str) or not pid.strip():
        project['id'] = f"proj-{str(uuid.uuid4())[:8]}"
        changed = True

    # Name
    name = project.get('name')
    if name is None:
        project['name'] = ''
        changed = True

    # Timestamps
    created_at = project.get('createdAt')
    updated_at = project.get('updatedAt')
    if not isinstance(created_at, str) or not created_at:
        # Prefer existing updatedAt if present, otherwise now
        project['createdAt'] = updated_at if isinstance(updated_at, str) and updated_at else now
        changed = True
    if not isinstance(updated_at, str) or not updated_at:
        project['updatedAt'] = now
        changed = True

    # Core fields
    status = project.get('status')
    if not isinstance(status, str) or not status:
        project['status'] = PROJECT_STATUS_PLANNING
        changed = True
    priority = project.get('priority')
    if not isinstance(priority, str) or not priority:
        project['priority'] = PROJECT_PRIORITY_MEDIUM
        changed = True

    # Progress (0-100)
    progress = project.get('progress')
    try:
        prog = int(progress) if progress is not None else 0
    except Exception:
        prog = 0
    if prog < 0:
        prog = 0
    if prog > 100:
        prog = 100
    if project.get('progress') != prog:
        project['progress'] = prog
        changed = True

    # Description & notes
    desc = project.get('description')
    if desc is None:
        project['description'] = ''
        changed = True
    notes = project.get('notes')
    if notes is None:
        project['notes'] = ''
        changed = True

    # Tags
    tags = project.get('tags')
    if tags is None:
        project['tags'] = []
        changed = True
    elif not isinstance(tags, list):
        project['tags'] = [str(tags)] if str(tags).strip() else []
        changed = True
    else:
        # Normalize to list[str] without empties
        nt = []
        for t in tags:
            s = str(t).strip()
            if s:
                nt.append(s)
        if nt != tags:
            project['tags'] = nt
            changed = True

    # Cost / Revenue (ensure dict with 'total' key)
    for key in ('cost', 'revenue'):
        v = project.get(key)
        if v is None:
            project[key] = {'total': 0}
            changed = True
        elif isinstance(v, (int, float)):
            project[key] = {'total': float(v)}
            changed = True
        elif isinstance(v, dict):
            total = v.get('total')
            try:
                tv = float(total) if total is not None else 0.0
            except Exception:
                tv = 0.0
            if tv < 0:
                tv = 0.0
            # Keep other keys, but ensure total is numeric
            if v.get('total') != tv:
                nv = dict(v)
                nv['total'] = tv
                project[key] = nv
                changed = True
        else:
            project[key] = {'total': 0}
            changed = True

    # Budget (number) and actual cost (number)
    budget = project.get('budget')
    budget_value = 0.0
    if isinstance(budget, dict):
        planned = budget.get('planned')
        if planned is None:
            planned = budget.get('total')
        if planned is None:
            planned = budget.get('amount')
        try:
            budget_value = float(planned) if planned is not None else 0.0
        except Exception:
            budget_value = 0.0
    elif isinstance(budget, (int, float)):
        budget_value = float(budget)
    elif budget is not None:
        try:
            budget_value = float(budget)
        except Exception:
            budget_value = 0.0
    if budget_value < 0:
        budget_value = 0.0
    if project.get('budget') != budget_value:
        project['budget'] = budget_value
        changed = True

    actual_cost = project.get('actualCost')
    if actual_cost is None:
        actual_cost = project.get('actual_cost')
    if actual_cost is None:
        cost_obj = project.get('cost')
        if isinstance(cost_obj, dict):
            actual_cost = cost_obj.get('total')
        elif isinstance(cost_obj, (int, float)):
            actual_cost = cost_obj
    actual_value = 0.0
    if isinstance(actual_cost, (int, float)):
        actual_value = float(actual_cost)
    elif actual_cost is not None:
        try:
            actual_value = float(actual_cost)
        except Exception:
            actual_value = 0.0
    if actual_value < 0:
        actual_value = 0.0
    if project.get('actualCost') != actual_value:
        project['actualCost'] = actual_value
        changed = True

    return project, changed


def normalize_agent_run(r: Any) -> Tuple[AgentRun, bool]:
    """Normalize a single agent run record, returning (run, changed)."""
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(r, dict):
        r = {}
        changed = True
    run: AgentRun = dict(r)

    # ID
    rid = run.get('id')
    if not isinstance(rid, str) or not rid.strip():
        run['id'] = f"run-{str(uuid.uuid4())[:8]}"
        changed = True

    # Timestamps
    for k in ('createdAt', 'updatedAt', 'startedAt'):
        v = run.get(k)
        if not isinstance(v, str) or not v:
            run[k] = now
            changed = True

    # Status
    status = run.get('status')
    if not isinstance(status, str) or not status:
        run['status'] = AGENT_RUN_STATUS_RUNNING
        changed = True

    # Optional fields
    for k in ('projectId', 'agentId', 'title', 'summary', 'finishedAt'):
        if k not in run:
            run[k] = None
            changed = True

    # Lists
    links = run.get('links')
    if links is None:
        run['links'] = []
        changed = True
    elif not isinstance(links, list):
        run['links'] = [links]
        changed = True

    tags = run.get('tags')
    if tags is None:
        run['tags'] = []
        changed = True
    elif not isinstance(tags, list):
        run['tags'] = [str(tags)] if str(tags).strip() else []
        changed = True

    # Dicts
    metrics = run.get('metrics')
    if metrics is None:
        run['metrics'] = {}
        changed = True
    elif not isinstance(metrics, dict):
        run['metrics'] = {}
        changed = True

    meta = run.get('meta')
    if meta is None:
        run['meta'] = {}
        changed = True
    elif not isinstance(meta, dict):
        run['meta'] = {}
        changed = True

    return run, changed


def normalize_agent_event(obj: Any) -> AgentEvent:
    """Normalize an event dict for read responses.
    
    NOTE: This does NOT write back to disk (events log is append-only).
    """
    if not isinstance(obj, dict):
        obj = {}

    out: AgentEvent = dict(obj)
    
    # Required-ish fields
    if 'id' not in out:
        out['id'] = None
    if 'ts' not in out:
        out['ts'] = None
    if 'type' not in out:
        out['type'] = 'note'
    if 'level' not in out:
        out['level'] = EVENT_LEVEL_INFO

    # Common linkage fields
    for k in ('projectId', 'runId', 'agentId'):
        if k not in out:
            out[k] = None

    # Display fields
    for k in ('title', 'message'):
        if k not in out:
            out[k] = None
    if 'data' not in out:
        out['data'] = None

    # Coerce types lightly (avoid raising)
    for k in ('id', 'ts', 'type', 'level', 'projectId', 'runId', 'agentId', 'title', 'message'):
        v = out.get(k)
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            continue
        out[k] = str(v)

    # Keep data as-is if it's JSON-ish; otherwise stringify
    dv = out.get('data')
    if dv is not None and not isinstance(dv, (dict, list, str, int, float, bool)):
        out['data'] = str(dv)

    return out


def project_get_tags(project: Project) -> List[str]:
    """Get deduplicated tags from project."""
    tags = project.get('tags')
    if not isinstance(tags, list):
        return []
    out = []
    for t in tags:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def normalize_agent_profile(obj: Any) -> Tuple[AgentProfile, bool]:
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(obj, dict):
        obj = {}
        changed = True
    profile: AgentProfile = dict(obj)

    pid = profile.get('id')
    if not isinstance(pid, str) or not pid.strip():
        profile['id'] = f"agent-{str(uuid.uuid4())[:8]}"
        changed = True

    name = str(profile.get('name') or '').strip()
    if not name:
        profile['name'] = 'Agent'
        changed = True
    elif name != profile.get('name'):
        profile['name'] = name
        changed = True

    for k in ('createdAt', 'updatedAt'):
        v = profile.get(k)
        if not isinstance(v, str) or not v:
            profile[k] = now
            changed = True

    if profile.get('role') is None:
        profile['role'] = 'general'
        changed = True

    if profile.get('description') is None:
        profile['description'] = ''
        changed = True

    tags = profile.get('styleTags')
    if tags is None:
        profile['styleTags'] = []
        changed = True
    elif not isinstance(tags, list):
        profile['styleTags'] = [str(tags)] if str(tags).strip() else []
        changed = True

    skills = profile.get('skills')
    if skills is None:
        profile['skills'] = []
        changed = True
    elif not isinstance(skills, list):
        profile['skills'] = [str(skills)] if str(skills).strip() else []
        changed = True

    if profile.get('outputMode') is None:
        profile['outputMode'] = 'concise'
        changed = True

    if profile.get('writebackPolicy') is None:
        profile['writebackPolicy'] = 'minimal'
        changed = True

    permissions = profile.get('permissions')
    if permissions is None:
        profile['permissions'] = {}
        changed = True
    elif not isinstance(permissions, dict):
        profile['permissions'] = {}
        changed = True

    meta = profile.get('meta')
    if meta is None:
        profile['meta'] = {}
        changed = True
    elif not isinstance(meta, dict):
        profile['meta'] = {}
        changed = True

    enabled = profile.get('enabled')
    enabled_bool = bool(enabled) if isinstance(enabled, bool) else str(enabled).lower() not in ('0', 'false', 'no', 'off', '')
    if profile.get('enabled') is not enabled_bool:
        profile['enabled'] = enabled_bool
        changed = True

    return profile, changed


def normalize_agent_capability(obj: Any) -> Tuple[AgentCapability, bool]:
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(obj, dict):
        obj = {}
        changed = True
    cap: AgentCapability = dict(obj)

    cid = cap.get('id')
    if not isinstance(cid, str) or not cid.strip():
        cap['id'] = f"cap-{str(uuid.uuid4())[:8]}"
        changed = True

    name = str(cap.get('name') or '').strip()
    if not name:
        cap['name'] = 'Capability'
        changed = True
    elif name != cap.get('name'):
        cap['name'] = name
        changed = True

    for k in ('createdAt', 'updatedAt'):
        v = cap.get(k)
        if not isinstance(v, str) or not v:
            cap[k] = now
            changed = True

    if cap.get('description') is None:
        cap['description'] = ''
        changed = True

    if cap.get('promptPack') is None:
        cap['promptPack'] = ''
        changed = True

    skill_pack = cap.get('skillPack')
    if skill_pack is None:
        cap['skillPack'] = []
        changed = True
    elif not isinstance(skill_pack, list):
        cap['skillPack'] = [str(skill_pack)] if str(skill_pack).strip() else []
        changed = True

    constraints = cap.get('constraints')
    if constraints is None:
        cap['constraints'] = []
        changed = True
    elif not isinstance(constraints, list):
        cap['constraints'] = [str(constraints)] if str(constraints).strip() else []
        changed = True

    meta = cap.get('meta')
    if meta is None:
        cap['meta'] = {}
        changed = True
    elif not isinstance(meta, dict):
        cap['meta'] = {}
        changed = True

    enabled = cap.get('enabled')
    enabled_bool = bool(enabled) if isinstance(enabled, bool) else str(enabled).lower() not in ('0', 'false', 'no', 'off', '')
    if cap.get('enabled') is not enabled_bool:
        cap['enabled'] = enabled_bool
        changed = True

    return cap, changed


def normalize_token_usage_record(obj: Any) -> Tuple[TokenUsageRecord, bool]:
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(obj, dict):
        obj = {}
        changed = True
    rec: TokenUsageRecord = dict(obj)

    rid = rec.get('id')
    if not isinstance(rid, str) or not rid.strip():
        rec['id'] = f"usage-{str(uuid.uuid4())[:8]}"
        changed = True

    ts = rec.get('ts')
    if not isinstance(ts, str) or not ts:
        rec['ts'] = now
        changed = True

    for k in ('projectId', 'runId', 'agentId', 'workspace', 'sessionId', 'source', 'model'):
        if k not in rec:
            rec[k] = None
            changed = True

    if rec.get('source') is None:
        rec['source'] = 'opencode'
        changed = True

    for k in ('promptTokens', 'completionTokens', 'totalTokens'):
        try:
            val = int(rec.get(k) or 0)
        except Exception:
            val = 0
        if val < 0:
            val = 0
        if rec.get(k) != val:
            rec[k] = val
            changed = True

    try:
        cost = float(rec.get('cost') or 0)
    except Exception:
        cost = 0.0
    if cost < 0:
        cost = 0.0
    if rec.get('cost') != cost:
        rec['cost'] = cost
        changed = True

    data = rec.get('data')
    if data is None:
        rec['data'] = {}
        changed = True
    elif not isinstance(data, dict):
        rec['data'] = {'raw': str(data)}
        changed = True

    return rec, changed
