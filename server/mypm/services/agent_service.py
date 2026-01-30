# -*- coding: utf-8 -*-
"""Agent runs business logic service."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

from ..domain.models import AgentRun
from ..domain.errors import AgentRunNotFoundError
from ..storage.agent_runs_json import AgentRunsStore


class AgentService:
    """Handles agent run-related business logic."""
    
    def __init__(self, store: AgentRunsStore):
        self.store = store
    
    def create_run(self, run_data: Dict) -> AgentRun:
        """Create new agent run (idempotent).
        
        Returns:
            Existing run if ID already exists, otherwise creates new run
        """
        run_id = str(run_data.get('id') or '').strip()
        if not run_id:
            run_id = f"run-{str(uuid.uuid4())[:8]}"
        
        # Check if run already exists (idempotency)
        data = self.store.load()
        existing = self.store.find_by_id(data, run_id)
        if existing:
            return existing
        
        # Create new run
        now = datetime.now().isoformat()
        run = {
            "id": run_id,
            "createdAt": now,
            "updatedAt": now,
            "startedAt": run_data.get('startedAt') or now,
            "finishedAt": run_data.get('finishedAt'),
            "status": run_data.get('status') or 'running',
            "projectId": run_data.get('projectId'),
            "agentId": run_data.get('agentId'),
            "title": run_data.get('title'),
            "summary": run_data.get('summary'),
            "links": run_data.get('links') if isinstance(run_data.get('links'), list) else [],
            "metrics": run_data.get('metrics') if isinstance(run_data.get('metrics'), dict) else {},
            "tags": run_data.get('tags') if isinstance(run_data.get('tags'), list) else [],
            "meta": run_data.get('meta') if isinstance(run_data.get('meta'), dict) else {},
        }
        
        runs = data.get('runs', []) or []
        runs.append(run)
        data['runs'] = runs
        self.store.save(data)
        
        return run
    
    def list_runs(
        self,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AgentRun], int]:
        """List agent runs with filtering and pagination.
        
        Returns:
            (runs, total_count)
        """
        data = self.store.load()
        runs = self.store.get_all(data)
        
        # Apply filters
        filtered = []
        for r in runs:
            if not isinstance(r, dict):
                continue
            if project_id and r.get('projectId') != project_id:
                continue
            if agent_id and r.get('agentId') != agent_id:
                continue
            if status and r.get('status') != status:
                continue
            filtered.append(r)
        
        # Sort by createdAt descending (most recent first)
        filtered.sort(key=lambda x: str(x.get('createdAt') or ''), reverse=True)
        
        # Paginate
        total = len(filtered)
        page = filtered[offset:offset + limit]
        
        return page, total
    
    def get_run(self, run_id: str) -> AgentRun:
        """Get single run by ID.
        
        Raises:
            AgentRunNotFoundError: If run doesn't exist
        """
        data = self.store.load()
        run = self.store.find_by_id(data, run_id)
        if not run:
            raise AgentRunNotFoundError(f"Run not found: {run_id}")
        return run
    
    def patch_run(self, run_id: str, patch: Dict) -> AgentRun:
        """Update agent run (PATCH semantics).
        
        Raises:
            AgentRunNotFoundError: If run doesn't exist
        """
        data = self.store.load()
        runs = data.get('runs', []) or []
        
        run = None
        for r in runs:
            if isinstance(r, dict) and r.get('id') == run_id:
                run = r
                break
        
        if not run:
            raise AgentRunNotFoundError(f"Run not found: {run_id}")
        
        # Apply patch (with type validation)
        protected = ['id', 'createdAt']
        for k, v in patch.items():
            if k in protected:
                continue
            if k == 'links' and not isinstance(v, list):
                continue
            if k == 'metrics' and not isinstance(v, dict):
                continue
            if k == 'tags' and not isinstance(v, list):
                continue
            if k == 'meta' and not isinstance(v, dict):
                continue
            run[k] = v
        
        run['updatedAt'] = datetime.now().isoformat()
        self.store.save(data)
        
        return run
