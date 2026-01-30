# -*- coding: utf-8 -*-
"""Agent runs storage layer (JSON file backend)."""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..domain.models import normalize_agent_run, AgentRun
from .atomic import write_json_atomic
from .locks import file_lock


class AgentRunsStore:
    """Manages agent_runs.json persistence with normalization."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> Dict:
        """Load agent runs data from JSON file.
        
        Returns:
            Dict with structure: {"version": "1.0.0", "lastUpdated": "...", "runs": [...]}
        """
        if not os.path.exists(self.file_path):
            data = {
                "version": "1.0.0",
                "lastUpdated": datetime.now().isoformat(),
                "runs": [],
            }
            self.save(data)
            return data

        obj = self._read_json()
        norm, changed = self._normalize_store(obj)
        if changed:
            self.save(norm)
        return norm
    
    def save(self, data: Dict):
        """Save agent runs data to JSON file atomically."""
        data['lastUpdated'] = datetime.now().isoformat()
        
        with file_lock(self.file_path):
            write_json_atomic(self.file_path, data)
    
    def _read_json(self) -> Optional[Dict]:
        """Read JSON file or return None if missing/corrupted."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception:
            return None
    
    def _normalize_store(self, raw) -> Tuple[Dict, bool]:
        """Normalize agent_runs.json content, returning (data, changed)."""
        changed = False
        now = datetime.now().isoformat()

        if not isinstance(raw, dict):
            raw = {}
            changed = True

        data = dict(raw)
        if not isinstance(data.get('version'), str) or not data.get('version'):
            data['version'] = '1.0.0'
            changed = True
        if not isinstance(data.get('lastUpdated'), str) or not data.get('lastUpdated'):
            data['lastUpdated'] = now
            changed = True

        runs = data.get('runs')
        if not isinstance(runs, list):
            runs = []
            data['runs'] = runs
            changed = True

        for i, r in enumerate(list(runs)):
            nr, ch = normalize_agent_run(r)
            if ch:
                runs[i] = nr
                changed = True

        return data, changed
    
    def find_by_id(self, data: Dict, run_id: str) -> Optional[AgentRun]:
        """Find run by ID in loaded data."""
        for r in data.get('runs', []) or []:
            if isinstance(r, dict) and r.get('id') == run_id:
                return r
        return None
    
    def get_all(self, data: Dict) -> List[AgentRun]:
        """Get all runs from loaded data."""
        return data.get('runs', []) or []
