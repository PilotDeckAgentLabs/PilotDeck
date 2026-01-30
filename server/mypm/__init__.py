# -*- coding: utf-8 -*-
"""MyProjectManager package."""

from .app import create_app
from .config import Config

__version__ = '1.0.0'

__all__ = [
    'create_app',
    'Config',
]
