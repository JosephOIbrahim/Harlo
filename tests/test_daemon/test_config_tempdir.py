"""D73 — TEMP_DIR detection.

The old fallback hardcoded /dev/shm on every non-Windows platform;
/dev/shm does not exist on macOS, so every Rule-30 dump silently
failed there (_dump_to_temp swallows OSError).
"""

import sys
import tempfile
from pathlib import Path

import pytest

from harlo.daemon import config
from harlo.daemon.config import _detect_temp_dir


def test_tmpdir_override_wins():
    result = _detect_temp_dir({"TMPDIR": "/custom"}, shm=Path("/nonexistent-shm"))
    assert result == Path("/custom")


def test_no_shm_falls_back_to_gettempdir():
    result = _detect_temp_dir({}, shm=Path("/nonexistent-shm"))
    assert result == Path(tempfile.gettempdir())


def test_existing_shm_preferred(tmp_path):
    # Linux branch: a real RAM-backed dir wins over gettempdir().
    assert _detect_temp_dir({}, shm=tmp_path) == tmp_path


@pytest.mark.skipif(sys.platform != "darwin", reason="D73 regression pin is macOS-specific")
def test_macos_temp_dir_exists_and_is_not_dev_shm():
    """The literal D73 regression pin: on macOS TEMP_DIR must be a real
    directory and must not be the nonexistent /dev/shm."""
    assert config.TEMP_DIR.is_dir()
    assert str(config.TEMP_DIR) != "/dev/shm"
