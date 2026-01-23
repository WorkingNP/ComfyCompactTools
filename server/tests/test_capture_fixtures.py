"""Tests for capture_fixtures script (offline, mocked HTTP)."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# We need to import the module under test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from capture_fixtures import (
    CaptureContext,
    generate_output_dir,
    get_object_info,
    create_job,
    get_job_status,
    wait_for_job,
    get_job_assets,
    download_asset,
)


class TestCaptureContext:
    """Tests for CaptureContext class."""

    def test_creates_output_directory(self, tmp_path: Path):
        """Test that context creates output directory."""
        output_dir = tmp_path / "test_capture"
        ctx = CaptureContext(output_dir, "test_workflow")
        assert output_dir.exists()

    def test_save_json(self, tmp_path: Path):
        """Test saving JSON data."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        data = {"key": "value", "number": 42}
        path = ctx.save_json("test.json", data)

        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_text(self, tmp_path: Path):
        """Test saving text data."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        text = "Hello, World!\nLine 2"
        path = ctx.save_text("test.txt", text)

        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == text

    def test_save_bytes(self, tmp_path: Path):
        """Test saving binary data."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        data = b"\x89PNG\r\n\x1a\n"
        path = ctx.save_bytes("test.bin", data)

        assert path.exists()
        with open(path, "rb") as f:
            loaded = f.read()
        assert loaded == data

    def test_add_error_simple(self, tmp_path: Path):
        """Test adding a simple error."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        ctx.add_error("Something went wrong")
        assert len(ctx.errors) == 1
        assert "Something went wrong" in ctx.errors[0]

    def test_add_error_with_exception(self, tmp_path: Path):
        """Test adding an error with exception."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            ctx.add_error("Operation failed", e)

        assert len(ctx.errors) == 1
        assert "Operation failed" in ctx.errors[0]
        assert "ValueError" in ctx.errors[0]
        assert "Test exception" in ctx.errors[0]

    def test_save_meta(self, tmp_path: Path):
        """Test saving capture metadata."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        ctx.job_id = "job_123"
        ctx.status = "completed"
        ctx.save_meta()

        meta_path = tmp_path / "capture_meta.json"
        assert meta_path.exists()

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["workflow_id"] == "test_workflow"
        assert meta["job_id"] == "job_123"
        assert meta["status"] == "completed"
        assert "timestamp" in meta
        assert "duration_seconds" in meta

    def test_save_error_summary(self, tmp_path: Path):
        """Test saving error summary."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        ctx.job_id = "job_456"
        ctx.add_error("Error 1: Connection failed")
        ctx.add_error("Error 2: Timeout")
        ctx.save_error_summary()

        summary_path = tmp_path / "error_summary.txt"
        assert summary_path.exists()

        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "test_workflow" in content
        assert "job_456" in content
        assert "Error 1" in content
        assert "Connection failed" in content
        assert "Error 2" in content
        assert "Timeout" in content

    def test_no_error_summary_when_no_errors(self, tmp_path: Path):
        """Test that error summary is not created when there are no errors."""
        ctx = CaptureContext(tmp_path, "test_workflow")
        ctx.save_error_summary()

        summary_path = tmp_path / "error_summary.txt"
        assert not summary_path.exists()


class TestGenerateOutputDir:
    """Tests for generate_output_dir function."""

    def test_generates_timestamped_dir(self, tmp_path: Path):
        """Test that output dir includes timestamp and workflow id."""
        result = generate_output_dir(tmp_path, "my_workflow")
        assert "my_workflow" in result.name
        # Should match pattern YYYYMMDD_HHMMSS_workflow_id
        parts = result.name.split("_")
        assert len(parts) >= 3
        # First part should be date (8 digits)
        assert len(parts[0]) == 8
        assert parts[0].isdigit()


class TestHTTPFunctions:
    """Tests for HTTP functions with mocked responses."""

    def test_get_object_info_success(self):
        """Test successful object_info fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"KSampler": {"inputs": {}}}
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response) as mock_get:
            result = get_object_info("http://localhost:8188")
            assert result == {"KSampler": {"inputs": {}}}
            mock_get.assert_called_once()

    def test_create_job_success(self):
        """Test successful job creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "job_123", "status": "queued"}
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.post", return_value=mock_response) as mock_post:
            result, _ = create_job(
                "http://localhost:8787",
                {"prompt": "test", "workflow_id": "test_wf"}
            )
            assert result["id"] == "job_123"
            mock_post.assert_called_once()

    def test_get_job_status_found(self):
        """Test getting job status when job exists."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "job_123", "status": "completed"},
            {"id": "job_456", "status": "running"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            result = get_job_status("http://localhost:8787", "job_123")
            assert result["id"] == "job_123"
            assert result["status"] == "completed"

    def test_get_job_status_not_found(self):
        """Test getting job status when job doesn't exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "job_456", "status": "running"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            result = get_job_status("http://localhost:8787", "job_123")
            assert result is None

    def test_wait_for_job_completed(self):
        """Test waiting for job that completes."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "job_123", "status": "completed", "result": "ok"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            job, status = wait_for_job("http://localhost:8787", "job_123", timeout_s=10)
            assert status == "completed"
            assert job["result"] == "ok"

    def test_wait_for_job_failed(self):
        """Test waiting for job that fails."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "job_123", "status": "failed", "error": "ComfyUI crashed"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            job, status = wait_for_job("http://localhost:8787", "job_123", timeout_s=10)
            assert status == "failed"
            assert job["error"] == "ComfyUI crashed"

    def test_wait_for_job_timeout(self):
        """Test waiting for job that times out."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "job_123", "status": "running"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            with patch("capture_fixtures.time.sleep"):  # Don't actually sleep
                job, status = wait_for_job(
                    "http://localhost:8787", "job_123", timeout_s=0.001
                )
                assert status == "timeout"

    def test_get_job_assets(self):
        """Test getting assets for a job."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "asset_1", "job_id": "job_123", "url": "/assets/img1.png"},
            {"id": "asset_2", "job_id": "job_456", "url": "/assets/img2.png"},
            {"id": "asset_3", "job_id": "job_123", "url": "/assets/img3.png"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response):
            assets = get_job_assets("http://localhost:8787", "job_123")
            assert len(assets) == 2
            assert all(a["job_id"] == "job_123" for a in assets)

    def test_download_asset(self):
        """Test downloading an asset."""
        mock_response = MagicMock()
        mock_response.content = b"\x89PNG\r\nfake image data"
        mock_response.raise_for_status = MagicMock()

        with patch("capture_fixtures.httpx.get", return_value=mock_response) as mock_get:
            result = download_asset("http://localhost:8787", "/assets/test.png")
            assert result == b"\x89PNG\r\nfake image data"
            mock_get.assert_called_with(
                "http://localhost:8787/assets/test.png", timeout=60.0
            )


class TestCaptureContextIntegration:
    """Integration tests for CaptureContext with file operations."""

    def test_full_failure_capture(self, tmp_path: Path):
        """Test capturing a full failure scenario."""
        ctx = CaptureContext(tmp_path, "failing_workflow")
        ctx.job_id = "job_fail_001"

        # Simulate saving request
        ctx.save_json("request.json", {"prompt": "test", "workflow_id": "failing_workflow"})

        # Simulate error during processing
        ctx.add_error("ComfyUI connection failed")
        ctx.add_error("Could not fetch object_info")
        ctx.status = "failed"

        # Save final state
        ctx.save_meta()
        ctx.save_error_summary()

        # Verify all files exist
        assert (tmp_path / "request.json").exists()
        assert (tmp_path / "capture_meta.json").exists()
        assert (tmp_path / "error_summary.txt").exists()

        # Verify meta content
        with open(tmp_path / "capture_meta.json", "r") as f:
            meta = json.load(f)
        assert meta["status"] == "failed"
        assert len(meta["errors"]) == 2

    def test_full_success_capture(self, tmp_path: Path):
        """Test capturing a full success scenario."""
        ctx = CaptureContext(tmp_path, "success_workflow")
        ctx.job_id = "job_success_001"

        # Simulate full capture
        ctx.save_json("request.json", {"prompt": "test"})
        ctx.save_json("object_info.json", {"KSampler": {}})
        ctx.save_json("job_response.json", {"id": "job_success_001", "status": "queued"})
        ctx.save_json("job_final.json", {"id": "job_success_001", "status": "completed"})
        ctx.save_bytes("sample_output.png", b"\x89PNG\r\nfake")
        ctx.save_json("assets.json", [{"id": "a1", "url": "/assets/test.png"}])

        ctx.status = "completed"
        ctx.save_meta()

        # Verify all files exist
        assert (tmp_path / "request.json").exists()
        assert (tmp_path / "object_info.json").exists()
        assert (tmp_path / "job_response.json").exists()
        assert (tmp_path / "job_final.json").exists()
        assert (tmp_path / "sample_output.png").exists()
        assert (tmp_path / "assets.json").exists()
        assert (tmp_path / "capture_meta.json").exists()

        # No error summary for success
        assert not (tmp_path / "error_summary.txt").exists()

        # Verify meta
        with open(tmp_path / "capture_meta.json", "r") as f:
            meta = json.load(f)
        assert meta["status"] == "completed"
        assert len(meta["errors"]) == 0
