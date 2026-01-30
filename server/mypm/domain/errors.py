# -*- coding: utf-8 -*-
"""Domain-specific errors."""


class MyPMError(Exception):
    """Base exception for MyProjectManager domain errors."""
    pass


class ProjectNotFoundError(MyPMError):
    """Project with given ID not found."""
    pass


class AgentRunNotFoundError(MyPMError):
    """Agent run with given ID not found."""
    pass


class ValidationError(MyPMError):
    """Invalid input data."""
    pass


class ConcurrencyConflictError(MyPMError):
    """Optimistic concurrency check failed (updatedAt mismatch)."""
    pass


class AuthenticationError(MyPMError):
    """Authentication required or invalid credentials."""
    pass
