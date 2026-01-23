import os
import uuid
from pathlib import Path

import pytest
from PIL import Image

import comfy_flux2_klein_generate as klein
from comfy_utils.image_checks import assert_not_blank_image


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get("RUN_KLEIN_BASE_TESTS", "0") != "1", reason="set RUN_KLEIN_BASE_TESTS=1 to run")
def test_flux2_klein_base_fp8_generates_image(base_url, tmp_path):
    root = Path(__file__).resolve().parents[1]
    template = root / "flux2_klein_base_4b_fp8_prompt_template.json"
    assert template.exists(), f"missing template: {template}"

    text_encoder = os.environ.get("KLEIN_TEXT_ENCODER", "qwen_3_4b.safetensors")
    unet = os.environ.get("KLEIN_UNET_BASE_FP8", "flux-2-klein-base-4b-fp8.safetensors")
    vae = os.environ.get("FLUX2_VAE", "flux2-vae.safetensors")

    prompt = klein.load_template(str(template))

    width, height = 512, 512
    # keep base test reasonably light; override via env if needed
    steps = int(os.environ.get("KLEIN_BASE_STEPS", "12"))
    cfg = float(os.environ.get("KLEIN_BASE_CFG", "4.0"))
    seed = 123456789
    prefix = f"pytest-klein-base-{uuid.uuid4().hex[:8]}"

    klein.set_params(
        prompt,
        text="test image, landscape photo, clear sky, sharp details",
        negative="",
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        seed=seed,
        sampler_name="euler",
        filename_prefix=prefix,
        text_encoder=text_encoder,
        unet=unet,
        vae=vae,
        batch=1,
    )

    prompt_id = klein.queue_prompt(base_url, prompt, client_id=str(uuid.uuid4()))
    hist_item = klein.wait_history(base_url, prompt_id, timeout_s=900)

    images = klein.extract_images(hist_item)
    assert images, f"history に images が見つかりません: keys={list(hist_item.keys())}"

    out_paths = [klein.download_image(base_url, meta, tmp_path) for meta in images]
    assert out_paths, "downloaded images list is empty"

    p = out_paths[0]
    assert p.exists() and p.stat().st_size > 0, f"output file missing/empty: {p}"

    with Image.open(p) as im:
        im.load()
        assert im.size == (width, height), f"unexpected image size: {im.size} != {(width, height)}"

    # Verify image is not blank (black/white)
    assert_not_blank_image(p)
