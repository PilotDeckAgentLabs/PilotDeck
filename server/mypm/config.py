# -*- coding: utf-8 -*-
"""Configuration management."""

import os


class Config:
    """Application configuration."""
    
    # Paths
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    DATA_DIR = os.path.join(ROOT_DIR, 'data')

    # SQLite runtime storage
    DB_FILE = os.environ.get('PM_DB_FILE') or os.path.join(DATA_DIR, 'pm.db')
    
    DEPLOY_LOG_FILE = os.path.join(ROOT_DIR, 'deploy_run.log')
    DEPLOY_STATE_FILE = os.path.join(ROOT_DIR, 'deploy_state.json')
    DEPLOY_UNIT_PREFIX = 'pilotdeck-deploy-'
    
    FRONTEND_DIST_DIR = os.path.join(ROOT_DIR, 'frontend', 'dist')
    
    # Server
    PORT = int(os.environ.get('PM_PORT', '8689'))
    DEBUG = bool(int(os.environ.get('PM_DEBUG', '0')))
    
    # Auth tokens
    ADMIN_TOKEN = os.environ.get('PM_ADMIN_TOKEN', '').strip()
    AGENT_TOKEN = os.environ.get('PM_AGENT_TOKEN', '').strip()
    
    # Static files (old UI)
    STATIC_FOLDER = os.path.join(ROOT_DIR, 'web')
    STATIC_URL_PATH = ''
