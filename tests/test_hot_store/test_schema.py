"""Tests for Hot Store schema creation and idempotency."""

from __future__ import annotations

import sqlite3

import pytest

from harlo.hot_store import HotStore
from harlo.hot_store.schema import ensure_schema


class TestSchemaCreation:
    """Tests for schema DDL and idempotency."""

    def test_schema_creates_hot_traces_table(self, tmp_db):
        """ensure_schema creates the hot_traces table."""
        conn = sqlite3.connect(tmp_db)
        try:
            ensure_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='hot_traces'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_creates_fts5_table(self, tmp_db):
        """ensure_schema creates the FTS5 virtual table."""
        conn = sqlite3.connect(tmp_db)
        try:
            ensure_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='hot_traces_fts'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_creates_triggers(self, tmp_db):
        """ensure_schema creates all three sync triggers."""
        conn = sqlite3.connect(tmp_db)
        try:
            ensure_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
            triggers = {row[0] for row in cursor.fetchall()}
            assert "hot_traces_ai" in triggers
            assert "hot_traces_ad" in triggers
            assert "hot_traces_au" in triggers
        finally:
            conn.close()

    def test_schema_creates_partial_index(self, tmp_db):
        """ensure_schema creates the pending partial index."""
        conn = sqlite3.connect(tmp_db)
        try:
            ensure_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name='idx_hot_traces_pending'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_idempotent(self, tmp_db):
        """Calling ensure_schema twice does not raise."""
        conn = sqlite3.connect(tmp_db)
        try:
            ensure_schema(conn)
            ensure_schema(conn)  # Should not raise
        finally:
            conn.close()

    def test_hotstore_init_creates_schema(self, tmp_db):
        """HotStore.__init__ creates schema automatically."""
        store = HotStore(tmp_db)
        conn = sqlite3.connect(tmp_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='hot_traces'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()
