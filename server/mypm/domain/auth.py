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


def generate_secret_key() -> str:
    """Generate a secure secret key for Flask session."""
    return secrets.token_hex(32)
