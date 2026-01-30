import pytest

from server.events import DEFAULT_WS_PREFS, normalize_ws_prefs, event_allowed


def test_normalize_ws_prefs_updates_known_keys_only():
    current = DEFAULT_WS_PREFS.copy()
    payload = {"job_progress": False, "assets": False, "unknown": True}
    updated = normalize_ws_prefs(payload, current)
    assert updated["job_progress"] is False
    assert updated["assets"] is False
    # unknown key should be ignored
    assert "unknown" not in updated


def test_event_allowed_respects_job_progress_flag():
    prefs = DEFAULT_WS_PREFS.copy()
    prefs["job_progress"] = False
    assert event_allowed("job_progress", prefs) is False
    assert event_allowed("job_update", prefs) is False


def test_event_allowed_respects_jobs_and_assets_flags():
    prefs = DEFAULT_WS_PREFS.copy()
    prefs["jobs"] = False
    prefs["assets"] = False
    assert event_allowed("job_created", prefs) is False
    assert event_allowed("jobs_snapshot", prefs) is False
    assert event_allowed("asset_created", prefs) is False
    assert event_allowed("assets_snapshot", prefs) is False
