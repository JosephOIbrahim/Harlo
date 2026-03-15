"""Tests for the semantic encoder and recall pipeline.

Verifies:
1. SDR format (2048-bit / 256-byte)
2. Semantic similarity (paraphrases closer than unrelated)
3. Semantic recall pipeline (store + recall roundtrip)
4. Lexical backward compatibility
5. Config-based encoder selection
"""

import json
import os
import tempfile

import pytest


class TestSemanticEncoderFormat:
    """Verify semantic encoder produces correct SDR format."""

    def test_sdr_is_256_bytes(self):
        """Semantic encoder must produce 256-byte (2048-bit) SDRs."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        sdr = enc.encode("The cat sat on the mat")
        assert len(sdr) == 256, f"Expected 256 bytes, got {len(sdr)}"

    def test_sdr_is_2048_bits(self):
        """SDR bit width must be 2048."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        sdr = enc.encode("Hello world")
        assert len(sdr) * 8 == 2048

    def test_deterministic(self):
        """Same input must produce identical SDR."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        sdr1 = enc.encode("determinism test")
        sdr2 = enc.encode("determinism test")
        assert sdr1 == sdr2

    def test_sparsity_reasonable(self):
        """SDR sparsity should be around 2-5% (TARGET_ACTIVE_BITS=80 of 2048)."""
        from src.encoder.semantic_encoder import SemanticEncoder, sdr_sparsity

        enc = SemanticEncoder()
        sdr = enc.encode("Testing sparsity of the representation")
        sp = sdr_sparsity(sdr)
        assert 0.01 < sp < 0.10, f"Sparsity {sp:.3f} outside expected range"

    def test_active_bits_near_target(self):
        """Number of active bits should be close to TARGET_ACTIVE_BITS (80)."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        sdr = enc.encode("Active bits count test")
        active = sum(bin(byte).count("1") for byte in sdr)
        assert 40 <= active <= 120, f"Active bits {active} outside expected range"

    def test_empty_text_raises(self):
        """Empty text must raise ValueError."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        with pytest.raises(ValueError):
            enc.encode("")

    def test_whitespace_only_raises(self):
        """Whitespace-only text must raise ValueError."""
        from src.encoder.semantic_encoder import SemanticEncoder

        enc = SemanticEncoder()
        with pytest.raises(ValueError):
            enc.encode("   ")


class TestSemanticSimilarity:
    """Verify paraphrases have lower hamming distance than unrelated sentences."""

    @pytest.fixture(scope="class")
    def encoder(self):
        from src.encoder.semantic_encoder import SemanticEncoder
        return SemanticEncoder()

    def test_paraphrases_closer_than_unrelated(self, encoder):
        """Paraphrases must have lower hamming distance than unrelated pairs."""
        from src.encoder.semantic_encoder import hamming_distance

        # Paraphrase pair
        a = encoder.encode("The cat sat on the mat")
        b = encoder.encode("A feline rested on the rug")
        paraphrase_dist = hamming_distance(a, b)

        # Unrelated pair
        c = encoder.encode("Quantum physics is complex")
        unrelated_dist = hamming_distance(a, c)

        assert paraphrase_dist < unrelated_dist, (
            f"Paraphrase distance ({paraphrase_dist}) should be less than "
            f"unrelated distance ({unrelated_dist})"
        )

    def test_rain_paraphrase(self, encoder):
        """Rain paraphrases should be close."""
        from src.encoder.semantic_encoder import hamming_distance

        a = encoder.encode("It's raining outside")
        b = encoder.encode("Rain is falling outdoors")
        c = encoder.encode("I love pizza")

        similar_dist = hamming_distance(a, b)
        unrelated_dist = hamming_distance(a, c)

        assert similar_dist < unrelated_dist

    def test_speed_paraphrase(self, encoder):
        """Speed/vehicle paraphrases should be close."""
        from src.encoder.semantic_encoder import hamming_distance

        a = encoder.encode("The car is fast")
        b = encoder.encode("The vehicle has high speed")
        c = encoder.encode("Space exploration is expensive")

        similar_dist = hamming_distance(a, b)
        unrelated_dist = hamming_distance(a, c)

        assert similar_dist < unrelated_dist

    def test_identical_text_zero_distance(self, encoder):
        """Identical text must have zero hamming distance."""
        from src.encoder.semantic_encoder import hamming_distance

        sdr = encoder.encode("exact match test")
        assert hamming_distance(sdr, sdr) == 0

    def test_batch_encode_matches_single(self, encoder):
        """Batch encoding must produce same results as single encoding."""
        texts = ["hello world", "goodbye world", "test phrase"]
        batch = encoder.encode_batch(texts)
        singles = [encoder.encode(t) for t in texts]

        for b, s in zip(batch, singles):
            assert b == s


class TestSemanticRecallPipeline:
    """Test the full semantic store + recall pipeline."""

    def test_store_and_recall_roundtrip(self):
        """Store traces with semantic encoding and recall them."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            semantic_store(db, "t1", "The cat sat on the mat", tags=["animal"])
            semantic_store(db, "t2", "Quantum physics equations", tags=["science"])
            semantic_store(db, "t3", "I love pizza and pasta", tags=["food"])

            result = semantic_recall(db, "A feline rested on a rug")

            assert result["confidence"] > 0.0
            assert len(result["traces"]) > 0
            # The cat trace should be the closest semantic match
            trace_ids = [t["trace_id"] for t in result["traces"]]
            assert "t1" in trace_ids
            # t1 should be closer than t2 (quantum physics)
            t1_dist = next(t["distance"] for t in result["traces"] if t["trace_id"] == "t1")
            t2_dist = next(t["distance"] for t in result["traces"] if t["trace_id"] == "t2")
            assert t1_dist < t2_dist, (
                f"Cat trace (dist={t1_dist}) should be closer than quantum trace (dist={t2_dist})"
            )
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_recall_empty_db(self):
        """Recall on empty database should return empty results."""
        from src.encoder import semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            result = semantic_recall(db, "anything")
            assert result["traces"] == []
            assert result["confidence"] == 0.0
            assert result["context"] == ""
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_recall_returns_context_string(self):
        """Recall should produce a non-empty context string."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            semantic_store(db, "t1", "Important memory about learning")
            result = semantic_recall(db, "learning")
            assert result["context"] != ""
            assert "Important memory" in result["context"]
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_recall_depth_normal_vs_deep(self):
        """Deep recall should return more traces than normal."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            for i in range(20):
                semantic_store(db, f"t{i}", f"Trace number {i} about topic {i % 3}")

            normal = semantic_recall(db, "topic", depth="normal")
            deep = semantic_recall(db, "topic", depth="deep")
            assert len(deep["traces"]) >= len(normal["traces"])
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_recall_confidence_range(self):
        """Confidence must be between 0.0 and 1.0."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            semantic_store(db, "t1", "test data for confidence")
            result = semantic_recall(db, "test")
            assert 0.0 <= result["confidence"] <= 1.0
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_store_with_tags_and_domain(self):
        """Tags and domain should be preserved through store/recall."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            semantic_store(db, "t1", "tagged trace", tags=["important", "test"], domain="testing")
            result = semantic_recall(db, "tagged trace")
            assert len(result["traces"]) > 0
            hit = result["traces"][0]
            assert hit["tags"] == ["important", "test"]
            assert hit["domain"] == "testing"
        finally:
            if os.path.exists(db):
                os.unlink(db)

    def test_traces_sorted_by_strength(self):
        """Results should be sorted by strength (descending)."""
        from src.encoder import semantic_store, semantic_recall

        db = tempfile.mktemp(suffix=".db")
        try:
            for i in range(10):
                semantic_store(db, f"t{i}", f"similar trace about memory number {i}")
            result = semantic_recall(db, "memory trace")
            strengths = [t["strength"] for t in result["traces"]]
            assert strengths == sorted(strengths, reverse=True)
        finally:
            if os.path.exists(db):
                os.unlink(db)


class TestLexicalBackwardCompatibility:
    """Verify the lexical encoder path still works via config."""

    def test_default_encoder_is_lexical(self):
        """Default ENCODER_TYPE should be 'lexical'."""
        # Only test when env var is not set
        original = os.environ.pop("TWIN_ENCODER_TYPE", None)
        try:
            # Re-import to pick up default
            import importlib
            from src.daemon import config
            importlib.reload(config)
            assert config.ENCODER_TYPE == "lexical"
        finally:
            if original is not None:
                os.environ["TWIN_ENCODER_TYPE"] = original

    def test_semantic_encoder_type_from_env(self):
        """TWIN_ENCODER_TYPE=semantic should set ENCODER_TYPE."""
        original = os.environ.get("TWIN_ENCODER_TYPE")
        try:
            os.environ["TWIN_ENCODER_TYPE"] = "semantic"
            import importlib
            from src.daemon import config
            importlib.reload(config)
            assert config.ENCODER_TYPE == "semantic"
        finally:
            if original is not None:
                os.environ["TWIN_ENCODER_TYPE"] = original
            else:
                os.environ.pop("TWIN_ENCODER_TYPE", None)


class TestRouterSemanticPath:
    """Test that the router correctly dispatches to semantic encoder."""

    def test_router_store_semantic(self):
        """Router should accept encoder='semantic' for store."""
        from src.daemon.router import route_command

        db = tempfile.mktemp(suffix=".db")
        try:
            # Temporarily override DB_PATH
            from src.daemon import config
            original_db = config.DB_PATH
            from pathlib import Path
            config.DB_PATH = Path(db)

            result = route_command("store", {
                "trace_id": "rt1",
                "message": "router test trace",
                "encoder": "semantic",
            })
            assert result["status"] == "ok"
            assert result["trace_id"] == "rt1"
        finally:
            config.DB_PATH = original_db
            if os.path.exists(db):
                os.unlink(db)

    def test_router_recall_semantic(self):
        """Router should accept encoder='semantic' for recall."""
        from src.daemon.router import route_command

        db = tempfile.mktemp(suffix=".db")
        try:
            from src.daemon import config
            original_db = config.DB_PATH
            from pathlib import Path
            config.DB_PATH = Path(db)

            # Store first
            route_command("store", {
                "trace_id": "rt1",
                "message": "The cat sat on the mat",
                "encoder": "semantic",
            })

            # Recall
            result = route_command("recall", {
                "query": "A feline on a rug",
                "encoder": "semantic",
            })
            assert result["status"] == "ok"
            assert len(result["result"]["traces"]) > 0
        finally:
            config.DB_PATH = original_db
            if os.path.exists(db):
                os.unlink(db)


class TestHammingDistance:
    """Test the Python hamming_distance function."""

    def test_identical_bytes_zero(self):
        """Identical bytes should have zero distance."""
        from src.encoder.semantic_encoder import hamming_distance
        a = bytes(256)
        assert hamming_distance(a, a) == 0

    def test_all_different_bits(self):
        """All-ones vs all-zeros should have distance 2048."""
        from src.encoder.semantic_encoder import hamming_distance
        a = bytes(256)
        b = bytes([0xFF] * 256)
        assert hamming_distance(a, b) == 2048

    def test_single_bit_difference(self):
        """One bit difference should have distance 1."""
        from src.encoder.semantic_encoder import hamming_distance
        a = bytes(256)
        b = bytearray(256)
        b[0] = 1
        assert hamming_distance(a, bytes(b)) == 1

    def test_length_mismatch_raises(self):
        """Mismatched lengths should raise AssertionError."""
        from src.encoder.semantic_encoder import hamming_distance
        with pytest.raises(AssertionError):
            hamming_distance(bytes(10), bytes(20))
