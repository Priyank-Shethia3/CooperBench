"""Evaluation backends - Modal, Docker, GCP Batch, etc."""

from cooperbench.eval.backends.base import EvalBackend, ExecResult, Sandbox
from cooperbench.eval.backends.modal import ModalBackend

__all__ = ["EvalBackend", "Sandbox", "ExecResult", "ModalBackend"]


def get_backend(name: str = "modal") -> EvalBackend:
    """Get an evaluation backend by name.

    Args:
        name: Backend name ("modal", "docker", "gcp_batch")

    Returns:
        EvalBackend instance
    """
    backends = {
        "modal": ModalBackend,
    }
    if name not in backends:
        available = ", ".join(sorted(backends.keys()))
        raise ValueError(f"Unknown backend: '{name}'. Available: {available}")
    return backends[name]()
