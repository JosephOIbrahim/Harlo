"""Async DMN teardown with preemption support.

Rule 19: New CLI commands during teardown MUST preempt.
Rule 30: On abort, dump to temp file, NOT SQLite.
Rule S6: CLI released in <50ms. Background synthesis up to 30s.
"""

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from .config import DMN_BUDGET_S, TEMP_DIR

_LOGGER = logging.getLogger(__name__)


class DMNTeardown:
    """Manages asynchronous DMN synthesis on session exit."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._abort_event = threading.Event()
        self._temp_file: Optional[Path] = None
        # Guards `_thread` mutation so that abort() and start() cannot
        # race on a half-replaced reference.  Without it, a rapid
        # close()→open()→close() sequence can leave abort() joining the
        # OLD thread while the NEW one runs unaborted (Rule 19 fail).
        self._state_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, synthesis_fn, context: dict, budget_s: float | None = None):
        """Start asynchronous teardown.

        Returns immediately (CLI released in <50ms).
        synthesis_fn runs in background for up to budget_s seconds
        (default DMN_BUDGET_S = 30, Rule S6).
        """
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                # In-lock abort: same code path as the public abort()
                # but we already hold the lock.
                self._abort_event.set()
                self._thread.join(timeout=0.01)

            # Fresh event per thread: if the old thread outlived the
            # 10ms join above, its (still-set) event keeps signalling
            # abort — clearing a SHARED event here would strand it
            # spinning until its deadline.
            self._abort_event = threading.Event()
            deadline = time.monotonic() + (
                budget_s if budget_s is not None else float(DMN_BUDGET_S)
            )
            self._thread = threading.Thread(
                target=self._run_synthesis,
                args=(synthesis_fn, context, deadline, self._abort_event),
                daemon=True,
            )
            self._thread.start()

    def abort(self):
        """Abort teardown in <10ms. Rule 19.

        Saves progress to temp file (Rule 30), not SQLite.
        """
        with self._state_lock:
            self._abort_event.set()
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=0.01)  # 10ms max wait

    def _run_synthesis(
        self,
        synthesis_fn,
        context: dict,
        deadline: float,
        abort_event: threading.Event,
    ):
        """Background synthesis with abort + budget checking (S6).

        `abort_event` is THIS thread's event (captured at start());
        reading self._abort_event here would race with a subsequent
        start() replacing it.
        """
        def _abort_check() -> bool:
            return abort_event.is_set() or time.monotonic() >= deadline

        try:
            result = synthesis_fn(context, abort_check=_abort_check)
            if abort_event.is_set():
                self._dump_to_temp(result)          # Rule 30: preempted
            elif time.monotonic() >= deadline:
                _LOGGER.warning("DMN synthesis exceeded %ss budget — partial dumped (Rule 30)", DMN_BUDGET_S)
                self._dump_to_temp(result)
            # else: committed by synthesis_fn (today: placeholder, commits nothing)
        except Exception:
            _LOGGER.exception("DMN synthesis error")   # replaces print(...stderr)

    def join_with_budget(self, timeout: float) -> bool:
        """Give background synthesis up to `timeout`s (Rule S6: 'daemon
        runs background synthesis up to 30 seconds. Then process
        exits'). Previously the daemon exited immediately, killing the
        daemon-thread at ~0s (D73). Returns True if synthesis finished,
        False if abandoned."""
        t = self._thread
        if t is None or not t.is_alive():
            return True
        t.join(timeout=timeout)
        if t.is_alive():
            _LOGGER.warning(
                "DMN synthesis still running after %.0fs budget — "
                "abandoning (daemon thread dies with process exit)", timeout)
            return False
        return True

    def _dump_to_temp(self, data):
        """Write partial results to temp file. Rule 30."""
        try:
            temp_path = TEMP_DIR / "twin_dmn_partial.json"
            with open(temp_path, "w") as f:
                json.dump(data, f)
            self._temp_file = temp_path
        except (OSError, TypeError, ValueError):
            pass  # Best effort — temp file is non-critical

    def recover_temp(self) -> Optional[dict]:
        """Recover partial results from temp file on boot."""
        path = TEMP_DIR / "twin_dmn_partial.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                path.unlink()  # Delete after recovery
                return data
            except (json.JSONDecodeError, OSError):
                path.unlink(missing_ok=True)
        return None


# Module-level singleton
_teardown = DMNTeardown()


def get_teardown() -> DMNTeardown:
    return _teardown
