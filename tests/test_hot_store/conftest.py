"""Fixtures for Hot Store tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from cognitive_twin.hot_store import HotStore


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_hot.db")


@pytest.fixture
def hot_store(tmp_db):
    """Provide a HotStore instance backed by a temporary database."""
    return HotStore(tmp_db)


@pytest.fixture
def sample_traces():
    """Provide sample trace data for testing."""
    return [
        {"message": "I had a productive meeting with the team today",
         "tags": ["work", "meeting"], "domain": "professional"},
        {"message": "Learning about quantum computing fundamentals",
         "tags": ["study", "physics"], "domain": "technical"},
        {"message": "Feeling grateful for the support from friends",
         "tags": ["personal", "emotions"], "domain": "personal"},
        {"message": "Debugging a memory leak in the Python application",
         "tags": ["coding", "python"], "domain": "technical"},
        {"message": "The weather was beautiful for a morning run",
         "tags": ["exercise", "weather"], "domain": "personal"},
    ]
