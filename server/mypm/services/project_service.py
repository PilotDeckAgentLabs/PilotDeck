# -*- coding: utf-8 -*-
"""Project business logic service."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

from ..domain.models import Project, project_get_tags
from ..domain.errors import ProjectNotFoundError, ValidationError, ConcurrencyConflictError
from ..storage import ProjectsStore


class ProjectService:
    """Handles project-related business logic."""
    
    def __init__(self, store: ProjectsStore):
        self.store = store
    
    def list_projects(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None
    ) -> Tuple[List[Project], Dict]:
        """Get all projects with optional filtering.
        
        Returns:
            (projects, metadata)
        """
        return self.store.list(status=status, priority=priority, category=category)
    
    def get_project(self, project_id: str) -> Project:
        """Get single project by ID.
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        project = self.store.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return project
    
    def create_project(self, project_data: Dict) -> Project:
        """Create new project.
        
        Raises:
            ValidationError: If required fields missing
        """
        try:
            return self.store.create(project_data or {})
        except ValueError as e:
            raise ValidationError(str(e))
    
    def update_project(self, project_id: str, updates: Dict) -> Project:
        """Update existing project (full PUT semantics).
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        try:
            return self.store.patch(project_id, updates or {}, if_updated_at=None)
        except KeyError:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
    
    def patch_project(
        self,
        project_id: str,
        patch: Dict,
        if_updated_at: Optional[str] = None
    ) -> Project:
        """Partial update for agents (PATCH semantics).
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
            ConcurrencyConflictError: If optimistic lock fails
        """
        try:
            return self.store.patch(project_id, patch or {}, if_updated_at=if_updated_at)
        except KeyError:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        except RuntimeError as e:
            raise ConcurrencyConflictError(str(e))
    
    def delete_project(self, project_id: str):
        """Delete project by ID.
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        try:
            self.store.delete(project_id)
        except KeyError:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
    
    def reorder_projects(self, ids: List[str]) -> List[Project]:
        """Reorder projects by ID list (for drag-drop persistence).
        
        Returns:
            Reordered project list
        """
        return self.store.reorder(ids or [])
    
    def batch_update(self, ops: List[Dict]) -> Tuple[List[Dict], bool]:
        """Batch update operations for agents.
        
        Args:
            ops: List of operations, each with:
                - id: project ID
                - patch: updates to apply
                - ifUpdatedAt: optional optimistic lock value
                - opId: optional operation ID for tracing
        
        Returns:
            (results, changed)
            results: List of result dicts with status per operation
            changed: Whether any operation succeeded
        """
        return self.store.batch_update(ops or [])
    
    def get_statistics(self) -> Dict:
        """Compute project statistics.
        
        Returns:
            Dict with aggregations by status/priority/category and financial totals
        """
        return self.store.get_statistics()
