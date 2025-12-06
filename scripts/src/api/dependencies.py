"""Dependency injection for FastAPI routes."""

from ..pipeline import PipelineOrchestrator

# Global orchestrator instance
_orchestrator: PipelineOrchestrator | None = None


def set_orchestrator(orchestrator: PipelineOrchestrator):
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> PipelineOrchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator
