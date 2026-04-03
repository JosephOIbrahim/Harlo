"""Tests for Hot Store FTS5 full-text search."""

from __future__ import annotations

import pytest

from harlo.hot_store import HotStore


class TestFTS5Search:
    """Tests for HotStore.search() using FTS5."""

    def test_search_finds_keyword(self, hot_store, sample_traces):
        """Search finds traces matching a keyword."""
        for t in sample_traces:
            hot_store.store(**t)

        results = hot_store.search("quantum")
        assert len(results) == 1
        assert "quantum" in results[0].message.lower()

    def test_search_finds_multiple(self, hot_store, sample_traces):
        """Search returns multiple matching traces."""
        for t in sample_traces:
            hot_store.store(**t)

        results = hot_store.search("the")
        assert len(results) >= 2

    def test_search_respects_limit(self, hot_store):
        """Search respects the limit parameter."""
        for i in range(20):
            hot_store.store(message=f"repeated keyword test {i}")

        results = hot_store.search("keyword", limit=5)
        assert len(results) == 5

    def test_search_no_results(self, hot_store, sample_traces):
        """Search returns empty list when nothing matches."""
        for t in sample_traces:
            hot_store.store(**t)

        results = hot_store.search("xyznonexistent")
        assert results == []

    def test_search_by_tag_content(self, hot_store):
        """Search matches tag content in FTS5 index."""
        hot_store.store(message="a simple note", tags=["specialtag"])

        results = hot_store.search("specialtag")
        assert len(results) == 1

    def test_search_by_domain(self, hot_store):
        """Search matches domain content in FTS5 index."""
        hot_store.store(message="some note", domain="neuroscience")

        results = hot_store.search("neuroscience")
        assert len(results) == 1

    def test_search_returns_correct_fields(self, hot_store):
        """Search results have all HotTrace fields populated."""
        hot_store.store(
            message="complete fields test",
            tags=["tag1"],
            domain="test_domain",
            trace_id="field_check",
            timestamp=1700000000.0,
        )

        results = hot_store.search("complete fields")
        assert len(results) == 1
        r = results[0]
        assert r.trace_id == "field_check"
        assert r.message == "complete fields test"
        assert r.tags == ["tag1"]
        assert r.domain == "test_domain"
        assert r.timestamp == 1700000000.0
        assert r.encoded is False

    def test_search_includes_encoded_traces(self, hot_store):
        """Search returns both encoded and un-encoded traces."""
        hot_store.store(message="encoded trace searchable", trace_id="enc")
        hot_store.store(message="pending trace searchable", trace_id="pend")
        hot_store.mark_encoded(["enc"])

        results = hot_store.search("searchable")
        assert len(results) == 2
