from __future__ import annotations

import random
from typing import Any, Dict, Optional


def build_txt2img_workflow(
    *,
    prompt: str,
    negative_prompt: str,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: Optional[int],
    batch_size: int,
    clip_skip: int = 1,
    vae: Optional[str] = None,
    filename_prefix: str = "cockpit",
) -> Dict[str, Any]:
    """Return a minimal ComfyUI workflow (API format).

    Notes:
    - This is the classic SD1.5-style graph:
      CheckpointLoaderSimple -> CLIPTextEncode (+/-) -> KSampler -> VAEDecode -> SaveImage
    - You can always replace this by exporting your own workflow via "File -> Export (API)" and
      then doing parameter substitution.
    """

    if seed is None or seed < 0:
        seed = random.randint(0, 2**31 - 1)

    # Node ids are strings in the API format.
    workflow: Dict[str, Any] = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": int(width), "height": int(height), "batch_size": int(batch_size)},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(cfg),
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
        },
    }

    clip_source = ["1", 1]
    if clip_skip and clip_skip > 1:
        workflow["8"] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"clip": ["1", 1], "stop_at_clip_layer": int(-abs(clip_skip))},
        }
        clip_source = ["8", 0]

    workflow["2"]["inputs"]["clip"] = clip_source
    workflow["3"]["inputs"]["clip"] = clip_source

    if vae:
        workflow["9"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae},
        }
        workflow["6"]["inputs"]["vae"] = ["9", 0]

    return workflow
