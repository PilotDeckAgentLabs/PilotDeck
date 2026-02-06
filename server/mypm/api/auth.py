# -*- coding: utf-8 -*-
"""Authentication API endpoints."""

import hashlib
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from ..storage.sqlite_db import connect

bp = Blueprint('auth', __name__)


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def _get_user_by_username(db_path: str, username: str):
    """Get user by username."""
    conn = connect(db_path)
    try:
        row = conn.execute(
            'SELECT id, username, password_hash, role, created_at, updated_at, last_login_at FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        if not row:
            return None
        return {
            'id': row['id'],
            'username': row['username'],
            'password_hash': row['password_hash'],
            'role': row['role'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'last_login_at': row['last_login_at'],
        }
    finally:
        conn.close()


def _update_last_login(db_path: str, user_id: str):
    """Update user's last login timestamp."""
    conn = connect(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            'UPDATE users SET last_login_at = ? WHERE id = ?',
            (now, user_id)
        )
        conn.commit()
    finally:
        conn.close()


@bp.route('/login', methods=['POST'])
def login():
    """Login endpoint.
    
    Request body:
        {
            "username": "admin",
            "password": "admin"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "user": {
                    "id": "...",
                    "username": "admin",
                    "role": "admin"
                }
            }
        }
    """
    from flask import current_app
    
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({
            'success': False,
            'error': '用户名和密码不能为空'
        }), 400
    
    # Get DB path from config
    db_path = current_app.config.get('DB_FILE')
    
    # Find user
    user = _get_user_by_username(db_path, username)
    if not user:
        return jsonify({
            'success': False,
            'error': '用户名或密码错误'
        }), 401
    
    # Verify password
    if not _verify_password(password, user['password_hash']):
        return jsonify({
            'success': False,
            'error': '用户名或密码错误'
        }), 401
    
    # Update last login
    _update_last_login(db_path, user['id'])
    
    # Set session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    
    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        }
    })


@bp.route('/me', methods=['GET'])
def me():
    """Get current user info from session.
    
    Response:
        {
            "success": true,
            "data": {
                "user": {
                    "id": "...",
                    "username": "admin",
                    "role": "admin"
                }
            }
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': '未登录'
        }), 401
    
    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': user_id,
                'username': session.get('username'),
                'role': session.get('role')
            }
        }
    })


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint.
    
    Response:
        {
            "success": true
        }
    """
    session.clear()
    return jsonify({
        'success': True
    })
