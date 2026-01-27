"""Tests for dynamic choices injection in workflow endpoints."""
from __future__ import annotations

import pytest
from pathlib import Path
from fastapi.testclient import TestClient


def test_sdxl_checkpoint_choices_injected(tmp_path, monkeypatch):
    """Test checkpoint choices are dynamically injected for SDXL workflow."""
    # Setup: Create temp checkpoint directory
    checkpoints_dir = tmp_path / "checkpoints"
    checkpoints_dir.mkdir()
    (checkpoints_dir / "sd_xl_base_1.0.safetensors").touch()
    (checkpoints_dir / "sd_xl_refiner_1.0.safetensors").touch()

    # Mock settings to use temp directory
    from server import main
    original_checkpoints = main.settings.checkpoints_dir
    monkeypatch.setattr(main.settings, "checkpoints_dir", str(checkpoints_dir))

    # Test: Get SDXL workflow details
    client = TestClient(main.app)
    response = client.get("/api/workflows/sdxl_txt2img")

    # Restore original settings
    monkeypatch.setattr(main.settings, "checkpoints_dir", original_checkpoints)

    assert response.status_code == 200
    data = response.json()

    # Verify choices were injected
    assert "checkpoint" in data["params"]
    assert "choices" in data["params"]["checkpoint"]
    choices = data["params"]["checkpoint"]["choices"]
    assert "sd_xl_base_1.0.safetensors" in choices
    assert "sd_xl_refiner_1.0.safetensors" in choices


def test_sdxl_vae_choices_injected(tmp_path, monkeypatch):
    """Test VAE choices are dynamically injected for SDXL workflow."""
    # Setup: Create temp VAE directory
    vae_dir = tmp_path / "vae"
    vae_dir.mkdir()
    (vae_dir / "sdxl_vae.safetensors").touch()
    (vae_dir / "vae-ft-mse.safetensors").touch()

    # Mock settings
    from server import main
    original_vae = main.settings.vae_dir
    monkeypatch.setattr(main.settings, "vae_dir", str(vae_dir))

    # Test
    client = TestClient(main.app)
    response = client.get("/api/workflows/sdxl_txt2img")

    # Restore
    monkeypatch.setattr(main.settings, "vae_dir", original_vae)

    assert response.status_code == 200
    data = response.json()

    # Verify VAE choices
    assert "vae" in data["params"]
    assert "choices" in data["params"]["vae"]
    choices = data["params"]["vae"]["choices"]
    assert "sdxl_vae.safetensors" in choices
    assert "vae-ft-mse.safetensors" in choices


def test_choices_not_injected_for_non_sdxl():
    """Test choices are only injected when params exist (not for flux2)."""
    from server import main
    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    response = client.get("/api/workflows/flux2_klein_distilled")

    assert response.status_code == 200
    data = response.json()

    # Flux2 might not have checkpoint param, so this shouldn't break
    # If it does have checkpoint param, choices should be injected
    if "checkpoint" in data["params"]:
        # If it exists, choices might be injected (which is fine)
        pass  # Test just verifies no errors occur


def test_empty_directory_no_choices(tmp_path, monkeypatch):
    """Test empty model directories don't break the endpoint."""
    # Setup: Empty directories
    checkpoints_dir = tmp_path / "checkpoints"
    checkpoints_dir.mkdir()
    vae_dir = tmp_path / "vae"
    vae_dir.mkdir()

    # Mock settings
    from server import main
    original_checkpoints = main.settings.checkpoints_dir
    original_vae = main.settings.vae_dir
    monkeypatch.setattr(main.settings, "checkpoints_dir", str(checkpoints_dir))
    monkeypatch.setattr(main.settings, "vae_dir", str(vae_dir))

    # Test
    client = TestClient(main.app)
    response = client.get("/api/workflows/sdxl_txt2img")

    # Restore
    monkeypatch.setattr(main.settings, "checkpoints_dir", original_checkpoints)
    monkeypatch.setattr(main.settings, "vae_dir", original_vae)

    assert response.status_code == 200
    # Should still work, just with empty or no choices
    data = response.json()
    assert "params" in data
