# -*- coding: utf-8 -*-
import json
import os
from typing import Dict, List, Optional

from .common import read_last_lines


class AgentEventsStore:
    def __init__(self, events_file: str):
        self.events_file = events_file

    def append(self, event: Dict):
        os.makedirs(os.path.dirname(self.events_file), exist_ok=True)
        with open(self.events_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def exists(self, event_id: str, max_lines: int = 5000) -> Optional[Dict]:
        if not event_id:
            return None
        lines = read_last_lines(self.events_file, max_lines=max_lines)
        for line in reversed(lines):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and obj.get('id') == event_id:
                return obj
        return None

    def normalize_for_read(self, obj) -> Dict:
        """Normalize an event dict for read responses without rewriting history."""
        if not isinstance(obj, dict):
            obj = {}
        out = dict(obj)

        if 'id' not in out:
            out['id'] = None
        if 'ts' not in out:
            out['ts'] = None
        if 'type' not in out:
            out['type'] = 'note'
        if 'level' not in out:
            out['level'] = 'info'

        for k in ('projectId', 'runId', 'agentId'):
            if k not in out:
                out[k] = None

        for k in ('title', 'message'):
            if k not in out:
                out[k] = None
        if 'data' not in out:
            out['data'] = None

        for k in ('id', 'ts', 'type', 'level', 'projectId', 'runId', 'agentId', 'title', 'message'):
            v = out.get(k)
            if v is None:
                continue
            if isinstance(v, (dict, list)):
                continue
            out[k] = str(v)

        dv = out.get('data')
        if dv is not None and not isinstance(dv, (dict, list, str, int, float, bool)):
            out['data'] = str(dv)

        return out

    def list(self, *, project_id: Optional[str], run_id: Optional[str], agent_id: Optional[str],
             typ: Optional[str], since_dt, limit: int, tail_lines: int) -> List[Dict]:
        # since_dt should be a datetime or None; parsing done in API layer.
        lines = read_last_lines(self.events_file, max_lines=tail_lines)
        out: List[Dict] = []
        for line in lines:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            obj = self.normalize_for_read(obj)
            if project_id and obj.get('projectId') != project_id:
                continue
            if run_id and obj.get('runId') != run_id:
                continue
            if agent_id and obj.get('agentId') != agent_id:
                continue
            if typ and obj.get('type') != typ:
                continue
            if since_dt:
                # API layer provides parse_iso helper
                ts = obj.get('ts')
                # comparisons handled outside; keep here simple and filter in API for now
                pass
            out.append(obj)

        if len(out) > limit:
            out = out[-limit:]
        return out
