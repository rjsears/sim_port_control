# =============================================================================
# API Routers
# =============================================================================
"""
FastAPI router modules.
"""

from app.routers import auth, discovery, logs, ports, simulators, switches, system, users

__all__ = [
    "auth",
    "discovery",
    "logs",
    "ports",
    "simulators",
    "switches",
    "system",
    "users",
]
