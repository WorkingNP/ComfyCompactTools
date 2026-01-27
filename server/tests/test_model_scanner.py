"""Tests for model scanner utility."""
from __future__ import annotations

import pytest
from pathlib import Path


def test_scan_empty_directory(tmp_path):
    """Test scanning empty directory returns empty list."""
    from server.model_scanner import scan_models

    result = scan_models(str(tmp_path))
    assert result == []


def test_scan_nonexistent_directory():
    """Test scanning nonexistent directory returns empty list."""
    from server.model_scanner import scan_models

    result = scan_models("/nonexistent/path/xyz")
    assert result == []


def test_scan_filters_by_extension(tmp_path):
    """Test that only specified extensions are returned."""
    from server.model_scanner import scan_models

    (tmp_path / "model1.safetensors").touch()
    (tmp_path / "model2.ckpt").touch()
    (tmp_path / "model3.pt").touch()
    (tmp_path / "README.txt").touch()
    (tmp_path / "config.json").touch()

    result = scan_models(str(tmp_path))
    assert len(result) == 3
    assert "model1.safetensors" in result
    assert "model2.ckpt" in result
    assert "model3.pt" in result
    assert "README.txt" not in result


def test_scan_returns_sorted(tmp_path):
    """Test that results are alphabetically sorted."""
    from server.model_scanner import scan_models

    (tmp_path / "zebra.safetensors").touch()
    (tmp_path / "alpha.safetensors").touch()
    (tmp_path / "beta.ckpt").touch()

    result = scan_models(str(tmp_path))
    assert result == ["alpha.safetensors", "beta.ckpt", "zebra.safetensors"]


def test_scan_returns_filenames_not_paths(tmp_path):
    """Test that only filenames are returned, not full paths."""
    from server.model_scanner import scan_models

    (tmp_path / "model.safetensors").touch()

    result = scan_models(str(tmp_path))
    assert result == ["model.safetensors"]
    assert "/" not in result[0]
    assert "\\" not in result[0]


def test_scan_checkpoints_wrapper(tmp_path):
    """Test convenience wrapper for checkpoints."""
    from server.model_scanner import scan_checkpoints

    (tmp_path / "sd_xl_base.safetensors").touch()
    result = scan_checkpoints(str(tmp_path))
    assert "sd_xl_base.safetensors" in result


def test_scan_vaes_wrapper(tmp_path):
    """Test convenience wrapper for VAEs."""
    from server.model_scanner import scan_vaes

    (tmp_path / "vae-ft-mse.safetensors").touch()
    result = scan_vaes(str(tmp_path))
    assert "vae-ft-mse.safetensors" in result


def test_scan_custom_extensions(tmp_path):
    """Test custom extension filtering."""
    from server.model_scanner import scan_models

    (tmp_path / "model.pth").touch()
    (tmp_path / "model.bin").touch()
    (tmp_path / "model.safetensors").touch()

    result = scan_models(str(tmp_path), extensions=[".pth", ".bin"])
    assert len(result) == 2
    assert "model.pth" in result
    assert "model.bin" in result
    assert "model.safetensors" not in result
