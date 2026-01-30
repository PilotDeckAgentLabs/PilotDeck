# -*- coding: utf-8 -*-
"""Projects storage layer (JSON file backend)."""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..domain.models import normalize_project, Project
from .atomic import write_json_atomic
from .locks import file_lock


class ProjectsStore:
    """Manages projects.json persistence with normalization."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> Dict:
        """Load projects data from JSON file.
        
        Backward compatibility:
        - If fields are missing or wrong-typed, fill defaults.
        - If any normalization happens, write back to disk.
        
        Returns:
            Dict with structure: {"version": "1.0.0", "lastUpdated": "...", "projects": [...]}
        """
        if not os.path.exists(self.file_path):
            data = {
                "version": "1.0.0",
                "lastUpdated": datetime.now().isoformat(),
                "projects": []
            }
            # Persist the initial structure so future tooling can rely on it.
            self.save(data)
            return data

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        data, changed = self._normalize_store(raw)
        if changed:
            self.save(data)
        return data
    
    def save(self, data: Dict):
        """Save projects data to JSON file atomically."""
        data["lastUpdated"] = datetime.now().isoformat()
        
        with file_lock(self.file_path):
            write_json_atomic(self.file_path, data)
    
    def _normalize_store(self, raw) -> Tuple[Dict, bool]:
        """Normalize projects.json content, returning (data, changed)."""
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

        projects = data.get('projects')
        if not isinstance(projects, list):
            projects = []
            data['projects'] = projects
            changed = True

        for i, p in enumerate(list(projects)):
            np, ch = normalize_project(p)
            if ch:
                projects[i] = np
                changed = True

        return data, changed
    
    def find_by_id(self, data: Dict, project_id: str) -> Optional[Project]:
        """Find project by ID in loaded data."""
        for p in data.get('projects', []) or []:
            if isinstance(p, dict) and p.get('id') == project_id:
                return p
        return None
    
    def get_all(self, data: Dict) -> List[Project]:
        """Get all projects from loaded data."""
        return data.get('projects', []) or []
