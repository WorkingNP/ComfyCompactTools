"""Tests for settings configuration."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_settings_default_directories():
    """Test that default checkpoint/VAE directories are set."""
    from server.main import get_settings

    settings = get_settings()
    assert hasattr(settings, 'checkpoints_dir')
    assert hasattr(settings, 'vae_dir')
    assert settings.checkpoints_dir
    assert settings.vae_dir
    assert Path(settings.checkpoints_dir).is_absolute()
    assert Path(settings.vae_dir).is_absolute()


def test_settings_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("COMFY_CHECKPOINTS_DIR", "/tmp/checkpoints")
    monkeypatch.setenv("COMFY_VAE_DIR", "/tmp/vae")

    # Need to reload settings after env change
    from server.main import get_settings
    settings = get_settings()

    assert settings.checkpoints_dir == "/tmp/checkpoints"
    assert settings.vae_dir == "/tmp/vae"


def test_settings_has_directories():
    """Test that settings has checkpoint and VAE directory attributes."""
    from server.main import settings

    # Verify the singleton settings instance has the new attributes
    assert hasattr(settings, 'checkpoints_dir')
    assert hasattr(settings, 'vae_dir')
    assert isinstance(settings.checkpoints_dir, str)
    assert isinstance(settings.vae_dir, str)
