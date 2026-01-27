"""
CockpitApiClient interface for interacting with the Cockpit HTTP API.

This is a Protocol (interface) that can be implemented by:
- RequestsCockpitApiClient: Real HTTP client using httpx
- FakeCockpitApiClient: Test double for unit tests
"""

from typing import Any, Dict, List, Protocol


class CockpitApiClient(Protocol):
    """Interface for calling Cockpit HTTP API."""

    def get_health(self) -> Dict[str, Any]:
        """
        Call GET /api/health.

        Returns:
            {
                "ok": bool,
                "comfy_url": str,
                "error_code": str | None,
                "error_message": str | None,
            }
        """
        ...

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        Call GET /api/workflows.

        Returns:
            [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "version": str,
                },
                ...
            ]
        """
        ...

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Call GET /api/workflows/{workflow_id}.

        Args:
            workflow_id: The workflow ID

        Returns:
            {
                "id": str,
                "name": str,
                "description": str,
                "version": str,
                "params": dict,
                "presets": dict,
            }

        Raises:
            Exception if workflow not found (404)
        """
        ...

    def create_job(
        self,
        workflow_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call POST /api/jobs.

        Args:
            workflow_id: The workflow ID to use
            params: Parameters for the job (e.g., {"prompt": "a cat", "seed": 42})

        Returns:
            {
                "id": str,
                "engine": str,
                "status": str,
                "prompt_id": str | None,
                "prompt": str,
                "params": dict,
                "created_at": str,
                "updated_at": str,
                "progress_value": float,
                "progress_max": float,
                "error": str | None,
            }
        """
        ...

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Call GET /api/jobs/{job_id}.

        Args:
            job_id: The job ID

        Returns:
            Same structure as create_job, with updated status/progress.
            May include "outputs": [...] when status is "completed".

        Raises:
            Exception if job not found (404)
        """
        ...
