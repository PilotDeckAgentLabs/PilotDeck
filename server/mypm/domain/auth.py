# -*- coding: utf-8 -*-
"""Authentication and authorization helpers."""

import os
import hmac
from typing import Tuple, Optional, Any

from flask import request, jsonify


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
