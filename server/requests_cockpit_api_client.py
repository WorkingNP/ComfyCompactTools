"""
Real HTTP implementation of CockpitApiClient using httpx.

Makes actual HTTP requests to the Cockpit server.
"""

import httpx
from typing import Any, Dict, List


class RequestsCockpitApiClient:
    """Real HTTP client for Cockpit API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787", timeout: float = 30.0):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the Cockpit server (e.g., "http://127.0.0.1:8787")
            timeout: Default timeout for requests in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_health(self) -> Dict[str, Any]:
        """Call GET /api/health."""
        url = f"{self.base_url}/api/health"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Call GET /api/workflows."""
        url = f"{self.base_url}/api/workflows"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Call GET /api/workflows/{workflow_id}.

        Raises:
            httpx.HTTPStatusError: If workflow not found (404)
        """
        url = f"{self.base_url}/api/workflows/{workflow_id}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def create_job(
        self,
        workflow_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call POST /api/jobs.

        Args:
            workflow_id: The workflow ID
            params: Job parameters (e.g., {"prompt": "a cat", "seed": 42})

        Returns:
            Job object from the API
        """
        url = f"{self.base_url}/api/jobs"
        payload = {
            "workflow_id": workflow_id,
            "params": params,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Call GET /api/jobs/{job_id}.

        Raises:
            httpx.HTTPStatusError: If job not found (404)
        """
        url = f"{self.base_url}/api/jobs/{job_id}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
