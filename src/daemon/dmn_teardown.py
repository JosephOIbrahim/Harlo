"""Async DMN teardown with preemption support.

Rule 19: New CLI commands during teardown MUST preempt.
Rule 30: On abort, dump to temp file, NOT SQLite.
Rule S6: CLI released in <50ms. Background synthesis up to 30s.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from .config import TEMP_DIR


class DMNTeardown:
    """Manages asynchronous DMN synthesis on session exit."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._abort_event = threading.Event()
        self._temp_file: Optional[Path] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, synthesis_fn, context: dict):
        """Start asynchronous teardown.

        Returns immediately (CLI released in <50ms).
        synthesis_fn runs in background for up to 30s.
        """
        if self.is_running:
            self.abort()

        self._abort_event.clear()
        self._thread = threading.Thread(
            target=self._run_synthesis,
            args=(synthesis_fn, context),
            daemon=True,
        )
        self._thread.start()

    def abort(self):
        """Abort teardown in <10ms. Rule 19.

        Saves progress to temp file (Rule 30), not SQLite.
        """
        self._abort_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.01)  # 10ms max wait

    def _run_synthesis(self, synthesis_fn, context: dict):
        """Background synthesis with abort checking."""
        try:
            result = synthesis_fn(context, abort_check=self._abort_event.is_set)
            if self._abort_event.is_set():
                # Rule 30: Dump to temp file on abort
                self._dump_to_temp(result)
            # If not aborted, result was committed by synthesis_fn
        except Exception:
            pass  # Synthesis failed, exit cleanly

    def _dump_to_temp(self, data):
        """Write partial results to temp file. Rule 30."""
        try:
            temp_path = TEMP_DIR / "twin_dmn_partial.json"
            with open(temp_path, "w") as f:
                json.dump(data, f)
            self._temp_file = temp_path
        except Exception:
            pass  # Best effort

    def recover_temp(self) -> Optional[dict]:
        """Recover partial results from temp file on boot."""
        candidates = [
            TEMP_DIR / "twin_dmn_partial.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    path.unlink()  # Delete after recovery
                    return data
                except Exception:
                    path.unlink(missing_ok=True)
        return None


# Module-level singleton
_teardown = DMNTeardown()


def get_teardown() -> DMNTeardown:
    return _teardown
