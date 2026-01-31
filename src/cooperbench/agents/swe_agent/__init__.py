"""Vendored SWE-agent for CooperBench.

This is a modified version of SWE-agent (https://github.com/SWE-agent/SWE-agent)
with support for multi-agent collaboration.

Original MIT License - see LICENSE file in this directory.
"""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "1.1.0-cooperbench"

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR  # For compatibility, point to package dir

# Config and tools directories within our package
CONFIG_DIR = Path(os.getenv("SWE_AGENT_CONFIG_DIR", PACKAGE_DIR / "config"))
TOOLS_DIR = Path(os.getenv("SWE_AGENT_TOOLS_DIR", PACKAGE_DIR / "tools"))

# Create trajectories dir if needed (for compatibility)
TRAJECTORY_DIR = Path(os.getenv("SWE_AGENT_TRAJECTORY_DIR", PACKAGE_DIR / "trajectories"))
TRAJECTORY_DIR.mkdir(exist_ok=True)


def get_agent_commit_hash() -> str:
    """Get the commit hash - returns static value for vendored version."""
    return "vendored"


def get_rex_commit_hash() -> str:
    """Get SWE-ReX commit hash."""
    try:
        import swerex
        from git import Repo

        repo = Repo(Path(swerex.__file__).resolve().parent.parent.parent, search_parent_directories=False)
        return repo.head.object.hexsha
    except Exception:
        return "unavailable"


def get_rex_version() -> str:
    """Get SWE-ReX version."""
    from swerex import __version__ as rex_version

    return rex_version


__all__ = [
    "PACKAGE_DIR",
    "CONFIG_DIR",
    "TOOLS_DIR",
    "TRAJECTORY_DIR",
    "REPO_ROOT",
    "get_agent_commit_hash",
    "get_rex_commit_hash",
    "get_rex_version",
    "__version__",
]
