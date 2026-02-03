# -*- coding: utf-8 -*-
"""Agent runs business logic service."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

from ..domain.models import AgentRun
from ..domain.errors import AgentRunNotFoundError
from ..storage import AgentRunsStore


class AgentService:
    """Handles agent run-related business logic."""
    
    def __init__(self, store: AgentRunsStore):
        self.store = store
    
    def create_run(self, run_data: Dict) -> AgentRun:
        """Create new agent run (idempotent).
        
        Returns:
            Existing run if ID already exists, otherwise creates new run
        """
        return self.store.create(run_data or {})
    
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
        return self.store.list(
            project_id=project_id,
            agent_id=agent_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    
    def get_run(self, run_id: str) -> AgentRun:
        """Get single run by ID.
        
        Raises:
            AgentRunNotFoundError: If run doesn't exist
        """
        run = self.store.get(run_id)
        if not run:
            raise AgentRunNotFoundError(f"Run not found: {run_id}")
        return run
    
    def patch_run(self, run_id: str, patch: Dict) -> AgentRun:
        """Update agent run (PATCH semantics).
        
        Raises:
            AgentRunNotFoundError: If run doesn't exist
        """
        try:
            return self.store.patch(run_id, patch or {})
        except KeyError:
            raise AgentRunNotFoundError(f"Run not found: {run_id}")
