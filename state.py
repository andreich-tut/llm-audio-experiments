"""
State module: Backward compatibility re-export from application/state.

This module provides a drop-in replacement for the old in-memory state system.
All functions maintain the same API but now persist to SQLite database.

On startup, automatically migrates data from legacy data/user_settings.json.
"""

# Backward compatibility: re-export from application layer
from application.state import *  # noqa: F401, F403
