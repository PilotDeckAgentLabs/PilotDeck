# -*- coding: utf-8 -*-
"""Project business logic service."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

from ..domain.models import Project, project_get_tags
from ..domain.errors import ProjectNotFoundError, ValidationError, ConcurrencyConflictError
from ..storage.projects_json import ProjectsStore


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
        data = self.store.load()
        projects = self.store.get_all(data)
        
        # Apply filters
        if status:
            projects = [p for p in projects if p.get('status') == status]
        if priority:
            projects = [p for p in projects if p.get('priority') == priority]
        if category:
            projects = [p for p in projects if p.get('category') == category]
        
        metadata = {
            "total": len(projects),
            "lastUpdated": data.get("lastUpdated")
        }
        return projects, metadata
    
    def get_project(self, project_id: str) -> Project:
        """Get single project by ID.
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        data = self.store.load()
        project = self.store.find_by_id(data, project_id)
        if not project:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return project
    
    def create_project(self, project_data: Dict) -> Project:
        """Create new project.
        
        Raises:
            ValidationError: If required fields missing
        """
        # Validate required fields
        if not project_data.get('name'):
            raise ValidationError("Project name cannot be empty")
        
        # Generate ID if not provided
        if "id" not in project_data:
            project_data["id"] = f"proj-{str(uuid.uuid4())[:8]}"
        
        # Set timestamps
        now = datetime.now().isoformat()
        project_data["createdAt"] = now
        project_data["updatedAt"] = now
        
        # Set defaults
        project_data.setdefault("status", "planning")
        project_data.setdefault("priority", "medium")
        project_data.setdefault("progress", 0)
        project_data.setdefault("description", "")
        project_data.setdefault("notes", "")
        project_data.setdefault("cost", {"total": 0})
        project_data.setdefault("revenue", {"total": 0})
        project_data.setdefault("tags", [])
        
        # Save
        data = self.store.load()
        data["projects"].append(project_data)
        self.store.save(data)
        
        return project_data
    
    def update_project(self, project_id: str, updates: Dict) -> Project:
        """Update existing project (full PUT semantics).
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        data = self.store.load()
        project = self.store.find_by_id(data, project_id)
        if not project:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        
        # Update fields (exclude protected fields)
        protected_fields = ["id", "createdAt"]
        for key, value in updates.items():
            if key not in protected_fields:
                project[key] = value
        
        project["updatedAt"] = datetime.now().isoformat()
        self.store.save(data)
        
        return project
    
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
        data = self.store.load()
        project = self.store.find_by_id(data, project_id)
        if not project:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        
        # Optional optimistic concurrency check
        if if_updated_at and str(project.get('updatedAt') or '') != str(if_updated_at):
            raise ConcurrencyConflictError(
                f"updatedAt mismatch: expected={if_updated_at}, actual={project.get('updatedAt')}"
            )
        
        # Apply patch (exclude protected fields)
        protected_fields = ["id", "createdAt"]
        for key, value in patch.items():
            if key not in protected_fields and key != 'ifUpdatedAt':
                project[key] = value
        
        project["updatedAt"] = datetime.now().isoformat()
        self.store.save(data)
        
        return project
    
    def delete_project(self, project_id: str):
        """Delete project by ID.
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        data = self.store.load()
        projects = data["projects"]
        
        # Find and remove
        for i, project in enumerate(projects):
            if project["id"] == project_id:
                del projects[i]
                self.store.save(data)
                return
        
        raise ProjectNotFoundError(f"Project not found: {project_id}")
    
    def reorder_projects(self, ids: List[str]) -> List[Project]:
        """Reorder projects by ID list (for drag-drop persistence).
        
        Returns:
            Reordered project list
        """
        data = self.store.load()
        projects = data.get("projects", [])
        
        by_id = {}
        for p in projects:
            pid = p.get('id')
            if pid:
                by_id[pid] = p
        
        new_projects = []
        seen = set()
        
        # Add projects in requested order
        for pid in ids:
            if pid in by_id and pid not in seen:
                new_projects.append(by_id[pid])
                seen.add(pid)
        
        # Append any projects not included in ids
        for p in projects:
            pid = p.get('id')
            if pid and pid not in seen:
                new_projects.append(p)
                seen.add(pid)
        
        data["projects"] = new_projects
        self.store.save(data)
        
        return new_projects
    
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
        data = self.store.load()
        projects = data.get('projects', []) or []
        by_id = {p.get('id'): p for p in projects if p.get('id')}
        
        results = []
        changed = False
        now = datetime.now().isoformat()
        
        for op in ops:
            op_id = None
            try:
                if not isinstance(op, dict):
                    raise ValueError('op must be an object')
                
                op_id = op.get('opId')
                pid = op.get('id')
                patch = op.get('patch')
                if_updated_at = op.get('ifUpdatedAt')
                
                if not pid or not isinstance(pid, str):
                    raise ValueError('id is required')
                if not isinstance(patch, dict):
                    raise ValueError('patch must be an object')
                
                project = by_id.get(pid)
                if not project:
                    results.append({
                        "opId": op_id,
                        "id": pid,
                        "success": False,
                        "error": f"Project not found: {pid}",
                        "status": 404,
                    })
                    continue
                
                # Optimistic concurrency check
                if if_updated_at and str(project.get('updatedAt') or '') != str(if_updated_at):
                    results.append({
                        "opId": op_id,
                        "id": pid,
                        "success": False,
                        "error": "Conflict: updatedAt mismatch",
                        "status": 409,
                        "data": {
                            "expectedUpdatedAt": if_updated_at,
                            "actualUpdatedAt": project.get('updatedAt'),
                        }
                    })
                    continue
                
                # Apply patch
                protected_fields = ["id", "createdAt"]
                for k, v in patch.items():
                    if k not in protected_fields:
                        project[k] = v
                
                project['updatedAt'] = now
                changed = True
                
                results.append({
                    "opId": op_id,
                    "id": pid,
                    "success": True,
                    "data": project,
                    "status": 200,
                })
                
            except Exception as e:
                results.append({
                    "opId": op_id,
                    "success": False,
                    "error": str(e),
                    "status": 400,
                })
        
        if changed:
            self.store.save(data)
        
        return results, changed
    
    def get_statistics(self) -> Dict:
        """Compute project statistics.
        
        Returns:
            Dict with aggregations by status/priority/category and financial totals
        """
        data = self.store.load()
        projects = self.store.get_all(data)
        
        stats = {
            "total": len(projects),
            "byStatus": {},
            "byPriority": {},
            "byCategory": {},
            "financial": {
                "totalBudget": 0,
                "totalCost": 0,
                "totalRevenue": 0,
                "netProfit": 0
            }
        }
        
        for p in projects:
            # Status aggregation
            status = p.get("status", "unknown")
            stats["byStatus"][status] = stats["byStatus"].get(status, 0) + 1
            
            # Priority aggregation
            priority = p.get("priority", "unknown")
            stats["byPriority"][priority] = stats["byPriority"].get(priority, 0) + 1
            
            # Category aggregation
            category = p.get("category", "未分类")
            stats["byCategory"][category] = stats["byCategory"].get(category, 0) + 1
            
            # Financial aggregation
            if "budget" in p and "planned" in p["budget"]:
                stats["financial"]["totalBudget"] += p["budget"]["planned"]
            if "cost" in p and "total" in p["cost"]:
                stats["financial"]["totalCost"] += p["cost"]["total"]
            if "revenue" in p and "total" in p["revenue"]:
                stats["financial"]["totalRevenue"] += p["revenue"]["total"]
        
        stats["financial"]["netProfit"] = (
            stats["financial"]["totalRevenue"] - stats["financial"]["totalCost"]
        )
        
        return stats
