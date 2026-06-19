"""D73 — DMN budget enforcement, join_with_budget, placeholder honesty.

Before D73: DMN_BUDGET_S was never read, the synthesis thread died at
~0s on process exit, and the placeholder synthesis was silent. These
tests pin the budget deadline (Rule S6), the Rule-30 partial dump, and
the plain-language honesty marker.

All coordination is Event-based — no sleeps.
"""

import json
import logging
import threading

import pytest

from harlo.daemon import dmn_teardown as dmn_module
from harlo.daemon.dmn_teardown import DMNTeardown


def test_abort_check_flips_after_budget(tmp_path, monkeypatch):
    """Budget expiry flips abort_check; the partial lands in TEMP_DIR
    (Rule 30) without any abort() call."""
    monkeypatch.setattr(dmn_module, "TEMP_DIR", tmp_path)
    td = DMNTeardown()
    never = threading.Event()  # never set — Event-coordinated wait, no sleeps

    def synth(ctx, abort_check=None):
        # Exits only when abort_check flips — here that can only be
        # the budget deadline.
        while not abort_check():
            never.wait(timeout=0.005)
        return {"partial": True}

    td.start(synth, {}, budget_s=0.05)
    td._thread.join(timeout=5)
    assert not td._thread.is_alive()

    dump = tmp_path / "twin_dmn_partial.json"
    assert dump.exists()
    assert json.loads(dump.read_text()) == {"partial": True}


def test_join_with_budget_finished_returns_true():
    """Finished (or never-started) synthesis joins immediately."""
    td = DMNTeardown()
    assert td.join_with_budget(1.0) is True  # no thread at all

    td.start(lambda ctx, abort_check=None: ctx, {})
    td._thread.join(timeout=5)
    assert td.join_with_budget(1.0) is True


def test_join_with_budget_abandons_and_logs(caplog):
    """A synthesis that outlives the join budget is abandoned, loudly."""
    td = DMNTeardown()
    release = threading.Event()

    def blocked(ctx, abort_check=None):
        release.wait(timeout=30)
        return ctx

    td.start(blocked, {})
    try:
        with caplog.at_level(logging.WARNING, logger="harlo.daemon.dmn_teardown"):
            assert td.join_with_budget(0.05) is False
        assert "budget" in caplog.text
    finally:
        release.set()  # release the thread (cleanup)
        td._thread.join(timeout=5)


def test_placeholder_synthesis_logs_honesty(tmp_path, caplog):
    """The placeholder synthesis announces itself (D73 honesty marker)."""
    from harlo.daemon.dmn_teardown import get_teardown
    from harlo.session import SessionManager

    mgr = SessionManager(db_path=str(tmp_path / "twin.db"), timeout_s=1800)
    session = mgr.create()

    with caplog.at_level(logging.INFO, logger="harlo.session.manager"):
        mgr.close(session.session_id, trigger_dmn=True)
        # The log fires on the background synthesis thread — join it
        # before asserting.
        get_teardown().join_with_budget(timeout=5)

    assert "PLACEHOLDER" in caplog.text
    assert session.session_id in caplog.text
