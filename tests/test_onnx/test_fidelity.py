"""Gate 1a: ONNX encoding fidelity test.

Validates that the ONNX encoder produces SDRs whose pairwise Hamming
distance relationships match the reference SemanticEncoder with
Pearson correlation >= 0.95.

This is the AND-chain blocker for Phase 1. If this fails, nothing proceeds.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from cognitive_twin.encoder.semantic_encoder import SemanticEncoder, hamming_distance
from cognitive_twin.encoder.onnx_encoder import OnnxEncoder

# Path to ONNX model
ONNX_MODEL_PATH = "models/bge-small-en-v1.5.onnx"

# Correlation threshold per spec
FIDELITY_THRESHOLD = 0.95


def _generate_corpus(n: int = 1000, seed: int = 42) -> list[str]:
    """Generate a deterministic synthetic corpus.

    Covers: short, medium, long messages across multiple domains.
    """
    rng = random.Random(seed)

    short_templates = [
        "I had a {adj} day at {place}",
        "Learning about {topic} today",
        "Feeling {emotion} this morning",
        "The {noun} was {adj}",
        "Met with {person} about {topic}",
        "Read an article on {topic}",
        "Working on {task} project",
        "Discovered a new {noun}",
        "Thinking about {topic} concepts",
        "Completed {task} successfully",
    ]

    adjectives = [
        "productive", "challenging", "exciting", "difficult", "wonderful",
        "interesting", "confusing", "rewarding", "frustrating", "peaceful",
        "creative", "intense", "quiet", "busy", "relaxing",
    ]

    places = [
        "work", "home", "the office", "the library", "the lab",
        "the park", "school", "the conference", "the meeting room",
    ]

    topics = [
        "quantum computing", "machine learning", "neuroscience",
        "philosophy", "mathematics", "distributed systems", "biology",
        "psychology", "economics", "art history", "climate science",
        "cryptography", "linguistics", "architecture", "music theory",
        "cognitive science", "graph theory", "robotics", "genetics",
        "astrophysics",
    ]

    emotions = [
        "grateful", "anxious", "motivated", "overwhelmed", "hopeful",
        "curious", "determined", "relaxed", "energetic", "reflective",
    ]

    nouns = [
        "algorithm", "pattern", "insight", "connection", "framework",
        "approach", "strategy", "technique", "method", "perspective",
    ]

    persons = [
        "the team", "a colleague", "the mentor", "a friend",
        "the advisor", "the professor", "the client",
    ]

    tasks = [
        "database migration", "code review", "system design",
        "documentation", "testing", "deployment", "refactoring",
        "debugging", "optimization", "prototyping",
    ]

    medium_templates = [
        "Today I spent time working on {topic}. The key insight was that {adj} "
        "approaches often lead to better results. I need to explore this further "
        "by reading more about {topic2}.",
        "Had a {adj} conversation with {person} about {topic}. We discussed "
        "the implications of recent developments and how they might affect our "
        "{task} project going forward.",
        "Reflecting on the {topic} lecture from yesterday. The connection between "
        "{topic} and {topic2} is becoming clearer. I should document these "
        "observations before I forget the details.",
    ]

    corpus: list[str] = []
    for i in range(n):
        if i % 5 < 3:  # 60% short
            template = rng.choice(short_templates)
            msg = template.format(
                adj=rng.choice(adjectives),
                place=rng.choice(places),
                topic=rng.choice(topics),
                emotion=rng.choice(emotions),
                noun=rng.choice(nouns),
                person=rng.choice(persons),
                task=rng.choice(tasks),
            )
        elif i % 5 < 4:  # 20% medium
            template = rng.choice(medium_templates)
            msg = template.format(
                adj=rng.choice(adjectives),
                topic=rng.choice(topics),
                topic2=rng.choice(topics),
                person=rng.choice(persons),
                task=rng.choice(tasks),
            )
        else:  # 20% longer composites
            parts = [
                rng.choice(short_templates).format(
                    adj=rng.choice(adjectives),
                    place=rng.choice(places),
                    topic=rng.choice(topics),
                    emotion=rng.choice(emotions),
                    noun=rng.choice(nouns),
                    person=rng.choice(persons),
                    task=rng.choice(tasks),
                )
                for _ in range(3)
            ]
            msg = ". ".join(parts) + "."

        corpus.append(msg)

    return corpus


@pytest.fixture(scope="module")
def reference_encoder():
    """Load SemanticEncoder (sentence-transformers, FP32)."""
    return SemanticEncoder()


@pytest.fixture(scope="module")
def onnx_encoder():
    """Load OnnxEncoder (ONNX Runtime)."""
    return OnnxEncoder(ONNX_MODEL_PATH)


@pytest.fixture(scope="module")
def corpus():
    """Generate the 1000-trace synthetic corpus."""
    return _generate_corpus(n=1000, seed=42)


@pytest.fixture(scope="module")
def reference_sdrs(reference_encoder, corpus):
    """Encode corpus with SemanticEncoder."""
    return reference_encoder.encode_batch(corpus)


@pytest.fixture(scope="module")
def onnx_sdrs(onnx_encoder, corpus):
    """Encode corpus with OnnxEncoder in batches."""
    batch_size = 64
    results = []
    for i in range(0, len(corpus), batch_size):
        batch = corpus[i : i + batch_size]
        results.extend(onnx_encoder.encode_batch(batch))
    return results


class TestOnnxFidelity:
    """Gate 1a: Encoding fidelity between ONNX and sentence-transformers."""

    def test_sdr_dimensions(self, onnx_sdrs):
        """All ONNX SDRs are 256 bytes."""
        for sdr in onnx_sdrs:
            assert len(sdr) == 256

    def test_sdr_sparsity(self, onnx_sdrs):
        """ONNX SDRs have approximately TARGET_ACTIVE_BITS active bits."""
        for sdr in onnx_sdrs:
            active = sum(bin(b).count("1") for b in sdr)
            assert 60 <= active <= 80, f"Active bits {active} outside [60, 80]"

    def test_pairwise_hamming_correlation(self, reference_sdrs, onnx_sdrs):
        """Pearson correlation of pairwise Hamming distances >= 0.95.

        This is the critical AND-chain gate. Compares 500 random pairs
        to verify that relative distance relationships are preserved.
        """
        rng = random.Random(123)
        n = len(reference_sdrs)
        num_pairs = 500

        pairs = set()
        while len(pairs) < num_pairs:
            i = rng.randint(0, n - 1)
            j = rng.randint(0, n - 1)
            if i != j:
                pairs.add((min(i, j), max(i, j)))

        h_ref = []
        h_onnx = []
        for i, j in pairs:
            h_ref.append(hamming_distance(reference_sdrs[i], reference_sdrs[j]))
            h_onnx.append(hamming_distance(onnx_sdrs[i], onnx_sdrs[j]))

        h_ref_arr = np.array(h_ref, dtype=np.float64)
        h_onnx_arr = np.array(h_onnx, dtype=np.float64)

        correlation = np.corrcoef(h_ref_arr, h_onnx_arr)[0, 1]

        assert correlation >= FIDELITY_THRESHOLD, (
            f"Hamming distance correlation {correlation:.4f} "
            f"< {FIDELITY_THRESHOLD} threshold. "
            f"ONNX encoder fails fidelity gate."
        )

    def test_semantic_ordering_preserved(self, reference_encoder, onnx_encoder):
        """Semantic similarity ordering is preserved between encoders.

        Similar pairs should have lower Hamming distance than dissimilar pairs.
        """
        similar_a = "The cat sat on the mat"
        similar_b = "A feline rested on the rug"
        dissimilar = "Quantum computing uses superposition"

        ref_a = reference_encoder.encode(similar_a)
        ref_b = reference_encoder.encode(similar_b)
        ref_d = reference_encoder.encode(dissimilar)

        onnx_a = onnx_encoder.encode(similar_a)
        onnx_b = onnx_encoder.encode(similar_b)
        onnx_d = onnx_encoder.encode(dissimilar)

        ref_similar_dist = hamming_distance(ref_a, ref_b)
        ref_dissimilar_dist = hamming_distance(ref_a, ref_d)

        onnx_similar_dist = hamming_distance(onnx_a, onnx_b)
        onnx_dissimilar_dist = hamming_distance(onnx_a, onnx_d)

        # Both encoders should rank similar < dissimilar
        assert ref_similar_dist < ref_dissimilar_dist
        assert onnx_similar_dist < onnx_dissimilar_dist
