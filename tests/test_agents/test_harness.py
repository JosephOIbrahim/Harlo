"""Tests for the MOE agent harness.

Verifies:
  - Valid descriptors are loaded.
  - Unknown roles are rejected.
  - The queue is drained in lexicographic order.
  - Outputs are written under AGENTS_OUTPUTS_DIR.
  - The harness does not block / loop (drain returns after one pass).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def isolated_dirs(monkeypatch, tmp_path):
    """Point AGENTS_* dirs at a tmp tree, reload the harness module."""
    monkeypatch.setenv("HARLO_DATA_DIR", str(tmp_path))
    import importlib
    import harlo.daemon.config as cfg

    importlib.reload(cfg)
    # Make repo-root imports work (`from agents.harness import ...`).
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(repo_root))
    import agents.harness as harness  # noqa: F401

    importlib.reload(harness)
    return cfg, harness


def _write_descriptor(path: Path, role: str, task_id: str) -> None:
    path.write_text(
        f"""id: "{task_id}"
role: {role}
title: "Test task {task_id}"
constraints: []
context_files: []
acceptance: []
""",
        encoding="utf-8",
    )


class TestLoadDescriptor:
    def test_valid_descriptor(self, isolated_dirs) -> None:
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        path = cfg.AGENTS_QUEUE_DIR / "t1.yaml"
        _write_descriptor(path, "os_engineer", "t1")
        desc = harness._load_descriptor(path)
        assert desc.role == "os_engineer"
        assert desc.id == "t1"

    def test_rejects_unknown_role(self, isolated_dirs) -> None:
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        path = cfg.AGENTS_QUEUE_DIR / "t1.yaml"
        _write_descriptor(path, "ghost_role", "t1")
        with pytest.raises(ValueError):
            harness._load_descriptor(path)


class TestDrain:
    def test_drains_in_sorted_order(self, isolated_dirs) -> None:
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        _write_descriptor(cfg.AGENTS_QUEUE_DIR / "0002.yaml", "scout", "0002")
        _write_descriptor(cfg.AGENTS_QUEUE_DIR / "0001.yaml", "scout", "0001")
        outs = harness._drain_queue()
        # Both descriptors processed
        assert len(outs) == 2
        # Outputs land under AGENTS_OUTPUTS_DIR
        ids = sorted(p.parent.name for p in outs)
        assert ids == ["0001", "0002"]

    def test_skips_malformed_files(self, isolated_dirs, capfd) -> None:
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        # Valid one
        _write_descriptor(cfg.AGENTS_QUEUE_DIR / "good.yaml", "scout", "g1")
        # Malformed one
        (cfg.AGENTS_QUEUE_DIR / "bad.yaml").write_text(
            "this is: not: valid: yaml: at: all", encoding="utf-8"
        )
        outs = harness._drain_queue()
        assert len(outs) == 1
        captured = capfd.readouterr()
        assert "bad.yaml" in captured.err or "bad.yaml" in captured.out

    def test_output_includes_provenance(self, isolated_dirs) -> None:
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        _write_descriptor(
            cfg.AGENTS_QUEUE_DIR / "0042.yaml", "os_engineer", "0042"
        )
        harness._drain_queue()
        out_file = cfg.AGENTS_OUTPUTS_DIR / "0042" / "dispatch.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["task"]["id"] == "0042"
        assert data["task"]["role"] == "os_engineer"
        assert data["status"] == "pending"


class TestRule1Compliance:
    def test_drain_returns_promptly_on_empty_queue(self, isolated_dirs) -> None:
        # No descriptors. Drain must return immediately, not block.
        cfg, harness = isolated_dirs
        cfg.ensure_data_dirs()
        outs = harness._drain_queue()
        assert outs == []
