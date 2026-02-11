# -*- coding: utf-8 -*-
"""Authentication and authorization helpers."""

import os
import hmac
import secrets
from typing import Tuple, Optional, Any
from functools import wraps

from flask import request, jsonify, session


def require_admin() -> Tuple[bool, Optional[Any]]:
    """Check if request has valid admin token.
    
    Returns:
        (True, None) if authorized
        (False, (response, status_code)) if unauthorized or misconfigured
    """
    token = os.environ.get('PM_ADMIN_TOKEN', '').strip()
    if not token:
        return False, (jsonify({
            "success": False,
            "error": "Admin token not configured. Set PM_ADMIN_TOKEN in service environment."
        }), 503)

    got = request.headers.get('X-PM-Token', '').strip()
    if not got or not hmac.compare_digest(got, token):
        return False, (jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401)
    return True, None


def require_agent() -> Tuple[bool, Optional[Any]]:
    """Optional auth for agent-facing APIs.

    If PM_AGENT_TOKEN is not set, the agent APIs are open (local-first default).
    If PM_AGENT_TOKEN is set, callers must send X-PM-Agent-Token.
    
    Returns:
        (True, None) if authorized or no auth required
        (False, (response, status_code)) if unauthorized
    """
    token = os.environ.get('PM_AGENT_TOKEN', '').strip()
    if not token:
        return True, None

    got = request.headers.get('X-PM-Agent-Token', '').strip()
    # Allow reuse of the admin header name for convenience when self-hosting.
    if not got:
        got = request.headers.get('X-PM-Token', '').strip()
    if not got or not hmac.compare_digest(got, token):
        return False, (jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401)
    return True, None


def require_login(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': '未登录'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_login_or_agent(f):
    """Decorator to require either web login (session) or agent token.
    
    This allows endpoints to be accessed by both:
    1. Web UI users (authenticated via session cookie)
    2. Agents (authenticated via X-PM-Agent-Token header)
    
    Use this for APIs that need to be accessible from both contexts,
    such as /api/projects endpoints that agents need to update.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session first (Web UI)
        if 'user_id' in session:
            return f(*args, **kwargs)
        
        # Check agent token (Agent API)
        ok, err = require_agent()
        if ok:
            return f(*args, **kwargs)
        
        # Both authentication methods failed
        return jsonify({
            'success': False,
            'error': '未登录'
        }), 401
    return decorated_function


def generate_secret_key() -> str:
    """Generate a secure secret key for Flask session."""
    return secrets.token_hex(32)
