"""Shared utilities for CooperBench.

Provides:
    console: Rich console for pretty output
    get_image_name: Generate Docker image names for tasks
    ResourceTracker: Track resources (sandboxes) for cleanup on exit
    setup_cleanup_handlers: Register SIGINT/SIGTERM handlers
"""

import atexit
import signal
import sys
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

from rich.console import Console

console = Console()

REGISTRY = "akhatua"
IMAGE_PREFIX = "cooperbench"


def get_image_name(repo_name: str, task_id: int) -> str:
    """Generate Docker Hub image name for a task."""
    repo_clean = repo_name.replace("_task", "").replace("_", "-")
    return f"{REGISTRY}/{IMAGE_PREFIX}-{repo_clean}:task{task_id}"


T = TypeVar("T")


class ResourceTracker(Generic[T]):
    """Thread-safe tracker for resources that need cleanup on exit."""

    def __init__(self, cleanup_fn: Callable[[T], None], name: str = "resource"):
        self._resources: list[T] = []
        self._lock = threading.Lock()
        self._cleanup_fn = cleanup_fn
        self._name = name

    def register(self, resource: T) -> None:
        """Register a resource for cleanup."""
        with self._lock:
            self._resources.append(resource)

    def unregister(self, resource: T) -> None:
        """Unregister a resource (already cleaned up)."""
        with self._lock:
            if resource in self._resources:
                self._resources.remove(resource)

    def cleanup_all(self) -> None:
        """Clean up all registered resources."""
        with self._lock:
            resources = list(self._resources)
        if resources:
            console.print(f"\n[yellow]cleaning up {len(resources)} {self._name}(s)...[/yellow]")
            for r in resources:
                try:
                    self._cleanup_fn(r)
                except Exception:
                    pass
            console.print("[green]done[/green]")


def setup_cleanup_handlers(tracker: ResourceTracker) -> None:
    """Setup SIGINT/SIGTERM handlers for graceful cleanup."""

    def handler(signum, frame):
        console.print("\n[yellow]interrupted - cleaning up...[/yellow]")
        tracker.cleanup_all()
        sys.exit(1)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    atexit.register(tracker.cleanup_all)


__all__ = [
    "console",
    "REGISTRY",
    "IMAGE_PREFIX",
    "get_image_name",
    "ResourceTracker",
    "setup_cleanup_handlers",
]
