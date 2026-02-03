# -*- coding: utf-8 -*-
"""Application factory."""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from .config import Config
from .storage import ProjectsStore, AgentRunsStore, AgentEventsStore
from .services import ProjectService, AgentService, DeployService
from .domain.auth import require_admin, require_agent


def create_app(config: Config = None) -> Flask:
    """Create and configure Flask application.
    
    Args:
        config: Configuration object (defaults to Config())
    
    Returns:
        Configured Flask app
    """
    if config is None:
        config = Config()
    
    # Create Flask app
    app = Flask(
        __name__,
        static_folder=config.STATIC_FOLDER,
        static_url_path=config.STATIC_URL_PATH
    )
    CORS(app)  # Allow CORS
    
    # Store config in app
    app.config.from_object(config)
    app.config['ROOT_DIR'] = config.ROOT_DIR
    
    # Initialize storage layer (SQLite)
    projects_store = ProjectsStore(config.DB_FILE)
    agent_runs_store = AgentRunsStore(config.DB_FILE)
    agent_events_store = AgentEventsStore(config.DB_FILE)
    
    # Initialize services
    project_service = ProjectService(projects_store)
    agent_service = AgentService(agent_runs_store)
    deploy_service = DeployService(
        root_dir=config.ROOT_DIR,
        state_file=config.DEPLOY_STATE_FILE,
        log_file=config.DEPLOY_LOG_FILE,
        unit_prefix=config.DEPLOY_UNIT_PREFIX
    )
    
    # Register in app extensions
    app.extensions.setdefault('stores', {})
    app.extensions['stores']['projects_store'] = projects_store
    app.extensions['stores']['agent_runs_store'] = agent_runs_store
    app.extensions['stores']['agent_events_store'] = agent_events_store
    
    app.extensions['projects_store'] = projects_store
    app.extensions['project_service'] = project_service
    app.extensions['agent_service'] = agent_service
    app.extensions['deploy_service'] = deploy_service
    app.extensions['require_agent'] = require_agent
    app.extensions['require_admin'] = require_admin

    # Maintenance flags (used for DB restore).
    app.extensions.setdefault('maintenance', {})
    app.extensions['maintenance'].setdefault('restoring_db', False)

    @app.before_request
    def _block_during_restore():
        # Keep admin endpoints available to complete restore request.
        from flask import request, jsonify

        maint = app.extensions.get('maintenance') or {}
        if not maint.get('restoring_db'):
            return None

        path = str(request.path or '')
        if path.startswith('/api/admin'):
            return None
        if path.startswith('/api/health') or path.startswith('/api/meta'):
            return None

        return jsonify({
            "success": False,
            "error": "Service is restoring database. Please retry shortly.",
        }), 503
    
    # Register blueprints
    from .api import projects, stats, meta, agent, admin_ops
    
    app.register_blueprint(projects.bp, url_prefix='/api/projects')
    app.register_blueprint(stats.bp, url_prefix='/api/stats')
    app.register_blueprint(meta.bp, url_prefix='/api')
    app.register_blueprint(agent.bp, url_prefix='/api/agent')
    app.register_blueprint(admin_ops.bp, url_prefix='/api/admin')
    
    # Register static routes
    @app.route('/')
    def index():
        """Serve old frontend."""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/app')
    @app.route('/app/')
    @app.route('/app/<path:filename>')
    def index_app(filename: str = 'index.html'):
        """Serve new Vite/Vue frontend if built.
        
        This keeps the current ops workflow:
        - Old UI remains at '/'
        - New UI (when built) is served at '/app'
        """
        if not os.path.isdir(config.FRONTEND_DIST_DIR):
            return (
                "<h2>New frontend not built</h2>"
                "<p>Run <code>npm install</code> and <code>npm run build</code> in <code>frontend/</code>.</p>"
                "<p>Current UI is available at <a href='/'>/</a>.</p>",
                200,
                {'Content-Type': 'text/html; charset=utf-8'}
            )

        path = str(filename or '').strip() or 'index.html'
        # Serve static assets if they exist, otherwise fall back to SPA index.
        full = os.path.join(config.FRONTEND_DIST_DIR, path)
        if path != 'index.html' and os.path.exists(full):
            return send_from_directory(config.FRONTEND_DIST_DIR, path)
        return send_from_directory(config.FRONTEND_DIST_DIR, 'index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify
        return jsonify({
            "success": False,
            "error": "资源未找到"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify
        return jsonify({
            "success": False,
            "error": "服务器内部错误"
        }), 500
    
    return app
