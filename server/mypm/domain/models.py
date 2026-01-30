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
