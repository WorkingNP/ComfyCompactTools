"""Fake ComfyUI client for testing without a real ComfyUI instance."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


class FakeComfyClient:
    """A fake ComfyUI client that simulates ComfyUI responses for testing.

    This client can be configured to:
    - Return successful responses
    - Simulate errors (unreachable, model missing, etc.)
    - Track submitted prompts for verification
    """

    def __init__(self, base_url: str = "http://fake-comfy:8188") -> None:
        self.base_url = base_url.rstrip("/")

        # Configuration flags
        self.is_reachable = True
        self.error_mode: Optional[str] = None  # "unreachable", "model_missing", "validation_error"

        # Tracking for test assertions
        self.submitted_prompts: List[Dict[str, Any]] = []
        self.last_prompt_id: Optional[str] = None

        # Configurable responses
        self.checkpoints = ["test-checkpoint.safetensors"]
        self.samplers = ["euler", "euler_ancestral", "dpm_2"]
        self.schedulers = ["normal", "karras", "simple"]
        self.vaes = ["test-vae.safetensors"]

    def ws_url(self, client_id: str) -> str:
        return f"ws://fake-comfy:8188/ws?clientId={client_id}"

    async def close(self) -> None:
        pass

    async def submit_prompt(self, prompt_workflow: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Simulate submitting a prompt to ComfyUI."""
        if not self.is_reachable:
            raise RuntimeError("ComfyUI error: Connection refused")

        if self.error_mode == "model_missing":
            raise RuntimeError("ComfyUI error: 400 Model not found: missing-model.safetensors")

        if self.error_mode == "validation_error":
            raise RuntimeError("ComfyUI error: 400 Invalid workflow structure")

        # Track the submission
        prompt_id = str(uuid.uuid4())
        self.last_prompt_id = prompt_id
        self.submitted_prompts.append({
            "prompt_id": prompt_id,
            "workflow": prompt_workflow,
            "client_id": client_id,
        })

        return {"prompt_id": prompt_id, "number": len(self.submitted_prompts)}

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Return fake history for a prompt."""
        if not self.is_reachable:
            raise RuntimeError("Connection refused")

        # Return a completed execution with one output image
        return {
            prompt_id: {
                "status": {"completed": True},
                "outputs": {
                    "7": {
                        "images": [
                            {
                                "filename": f"fake_output_{prompt_id[:8]}.png",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                },
            }
        }

    async def get_view_image(self, *, filename: str, subfolder: str, folder_type: str) -> bytes:
        """Return fake image bytes."""
        if not self.is_reachable:
            raise RuntimeError("Connection refused")

        # Return a minimal valid PNG (1x1 transparent pixel)
        # PNG signature + IHDR + IDAT + IEND
        return (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )

    async def get_models_in_folder(self, folder: str) -> List[str]:
        """Return fake model list based on folder type."""
        if not self.is_reachable:
            raise RuntimeError("Connection refused")

        if folder == "checkpoints":
            return self.checkpoints
        elif folder == "vae":
            return self.vaes
        return []

    async def get_object_info(self, node_class: Optional[str] = None) -> Dict[str, Any]:
        """Return fake object info."""
        if not self.is_reachable:
            raise RuntimeError("Connection refused")

        if node_class == "KSampler":
            return {
                "KSampler": {
                    "input": {
                        "required": {
                            "sampler_name": [self.samplers],
                            "scheduler": [self.schedulers],
                        }
                    }
                }
            }

        if node_class == "VAELoader":
            return {
                "VAELoader": {
                    "input": {
                        "required": {
                            "vae_name": [self.vaes],
                        }
                    }
                }
            }

        return {}

    async def get_ksampler_options(self) -> Dict[str, List[str]]:
        """Return fake KSampler options."""
        if not self.is_reachable:
            return {}

        return {
            "sampler_name": self.samplers,
            "scheduler": self.schedulers,
        }

    async def check_health(self) -> Dict[str, Any]:
        """Check ComfyUI health status with detailed error info."""
        if not self.is_reachable:
            return {
                "ok": False,
                "error_code": "COMFY_UNREACHABLE",
                "error_message": "Cannot connect to ComfyUI server",
                "comfy_url": self.base_url,
            }

        if self.error_mode == "model_missing":
            return {
                "ok": False,
                "error_code": "MODEL_MISSING",
                "error_message": "Required model not found",
                "comfy_url": self.base_url,
            }

        return {
            "ok": True,
            "error_code": None,
            "error_message": None,
            "comfy_url": self.base_url,
            "models_loaded": len(self.checkpoints),
        }

    # Test helper methods
    def set_unreachable(self) -> None:
        """Simulate ComfyUI being unreachable."""
        self.is_reachable = False

    def set_reachable(self) -> None:
        """Restore ComfyUI reachability."""
        self.is_reachable = True
        self.error_mode = None

    def set_error_mode(self, mode: str) -> None:
        """Set error simulation mode: 'model_missing', 'validation_error', etc."""
        self.error_mode = mode

    def reset(self) -> None:
        """Reset all state for fresh test."""
        self.is_reachable = True
        self.error_mode = None
        self.submitted_prompts = []
        self.last_prompt_id = None
