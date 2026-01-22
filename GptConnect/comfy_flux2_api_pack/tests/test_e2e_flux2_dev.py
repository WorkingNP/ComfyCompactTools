import os
import uuid
from pathlib import Path

from PIL import Image

import comfy_flux2_generate as dev


def test_flux2_dev_generates_image(base_url, tmp_path):
    root = Path(__file__).resolve().parents[1]
    template = root / "flux2_dev_prompt_template.json"
    assert template.exists(), f"missing template: {template}"

    text_encoder = os.environ.get("FLUX2_DEV_TEXT_ENCODER", "mistral_3_small_flux2_bf16.safetensors")
    unet = os.environ.get("FLUX2_DEV_UNET", "flux2_dev_fp8mixed.safetensors")
    vae = os.environ.get("FLUX2_VAE", "flux2-vae.safetensors")

    prompt = dev.load_template(str(template))
    prompt["47"]["inputs"]["batch_size"] = 1

    width, height = 512, 512
    steps = 10
    guidance = 4.0
    seed = 123456789

    prefix = f"pytest-flux2-dev-{uuid.uuid4().hex[:8]}"

    dev.set_common_params(
        prompt,
        text="test image, simple subject, high contrast",
        width=width,
        height=height,
        steps=steps,
        guidance=guidance,
        seed=seed,
        sampler_name="euler",
        filename_prefix=prefix,
        text_encoder=text_encoder,
        unet=unet,
        vae=vae,
    )

    prompt_id = dev.queue_prompt(base_url, prompt, client_id=str(uuid.uuid4()))
    hist_item = dev.wait_history(base_url, prompt_id, timeout_s=600)

    images = dev.extract_images(hist_item)
    assert images, f"history に images が見つかりません: keys={list(hist_item.keys())}"

    out_paths = [dev.download_image(base_url, meta, tmp_path) for meta in images]
    assert out_paths, "downloaded images list is empty"

    # validate first image
    p = out_paths[0]
    assert p.exists() and p.stat().st_size > 0, f"output file missing/empty: {p}"

    with Image.open(p) as im:
        im.load()
        assert im.size == (width, height), f"unexpected image size: {im.size} != {(width, height)}"
