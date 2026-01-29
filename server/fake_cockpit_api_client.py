"""
Fake implementation of CockpitApiClient for testing.

Does not make any HTTP requests. Returns predefined responses.
"""

from typing import Any, Dict, List


class FakeCockpitApiClient:
    """Fake API client for testing MCP tools."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787"):
        self.base_url = base_url
        self.jobs_created: List[Dict[str, Any]] = []
        self.jobs_db: Dict[str, Dict[str, Any]] = {}
        self._job_counter = 0
        self.auto_complete = False
        self.fail_on_job_number = None
        self._health_response = {
            "ok": True,
            "comfy_url": "http://127.0.0.1:8188",
            "error_code": None,
            "error_message": None,
        }

    def set_health_response(self, response: Dict[str, Any]):
        """Override health response for testing."""
        self._health_response = response

    def get_health(self) -> Dict[str, Any]:
        """Mock GET /api/health."""
        return self._health_response

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Mock GET /api/workflows."""
        return [
            {
                "id": "flux2_klein_distilled",
                "name": "Flux 2 Klein Distilled",
                "description": "Fast 4-step generation",
                "version": "1.0.0",
            },
            {
                "id": "sd15_txt2img",
                "name": "SD 1.5 Text-to-Image",
                "description": "Classic SD 1.5",
                "version": "1.0.0",
            },
        ]

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Mock GET /api/workflows/{workflow_id}."""
        if workflow_id == "flux2_klein_distilled":
            return {
                "id": "flux2_klein_distilled",
                "name": "Flux 2 Klein Distilled",
                "description": "Fast 4-step generation",
                "version": "1.0.0",
                "params": {
                    "prompt": {"type": "string", "required": True},
                    "width": {"type": "integer", "default": 832},
                    "height": {"type": "integer", "default": 1024},
                    "seed": {"type": "integer", "default": -1},
                },
                "presets": {},
            }
        elif workflow_id == "sd15_txt2img":
            return {
                "id": "sd15_txt2img",
                "name": "SD 1.5 Text-to-Image",
                "description": "Classic SD 1.5",
                "version": "1.0.0",
                "params": {
                    "prompt": {"type": "string", "required": True},
                    "steps": {"type": "integer", "default": 20},
                },
                "presets": {},
            }
        else:
            raise ValueError(f"Workflow not found: {workflow_id}")

    def create_job(
        self,
        workflow_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mock POST /api/jobs."""
        self._job_counter += 1
        if self.fail_on_job_number is not None:
            if self._job_counter == self.fail_on_job_number:
                raise Exception(f"Simulated failure for job {self._job_counter}")
        job_id = f"job_{self._job_counter}"
        job = {
            "id": job_id,
            "engine": "comfy",
            "status": "queued",
            "prompt_id": f"prompt_{self._job_counter}",
            "prompt": params.get("prompt", ""),
            "negative_prompt": "",
            "params": params,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "progress_value": 0,
            "progress_max": 100,
            "error": None,
        }
        if self.auto_complete:
            job["status"] = "completed"
            job["outputs"] = [f"{job_id}.png"]
            job["progress_value"] = 100
        self.jobs_created.append(job)
        self.jobs_db[job_id] = job
        return job

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Mock GET /api/jobs/{job_id}."""
        if job_id not in self.jobs_db:
            raise ValueError(f"Job not found: {job_id}")
        return self.jobs_db[job_id]

    def set_job_completed(self, job_id: str, outputs: List[str]):
        """Helper to simulate job completion (for testing)."""
        if job_id in self.jobs_db:
            self.jobs_db[job_id]["status"] = "completed"
            self.jobs_db[job_id]["outputs"] = outputs
            self.jobs_db[job_id]["progress_value"] = 100

    def set_job_failed(self, job_id: str, error: str):
        """Helper to simulate job failure (for testing)."""
        if job_id in self.jobs_db:
            self.jobs_db[job_id]["status"] = "failed"
            self.jobs_db[job_id]["error"] = error
