"""
Semantic SDR encoder using sentence-transformers + LSH projection.

Produces the same 2048-bit SDR format as the Rust lexical encoder,
so hamming_distance works identically on both.

Pipeline:
    text → sentence-transformers → 384-dim float embedding
    → LSH projection → top-k bit selection → 2048-bit SDR (bytes)
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional

# Match the Rust encoder constants
SDR_WIDTH = 2048
TARGET_ACTIVE_BITS = 80
PROJECTION_SEED = 42
EMBEDDING_DIM = 384  # BGE-small-en-v1.5


class SemanticEncoder:
    """Semantic encoder that maps text to sparse bitvectors via BGE embeddings."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """Load the embedding model and pre-compute the LSH projection matrix.

        Args:
            model_name: HuggingFace model name. Default uses BGE-small (384-dim).
        """
        self.model = SentenceTransformer(model_name)
        self.projection_matrix = self._create_projection_matrix()

    def _create_projection_matrix(self) -> np.ndarray:
        """Create deterministic LSH projection matrix.

        Uses the same seed as the Rust encoder for consistency.
        Returns: (SDR_WIDTH, EMBEDDING_DIM) matrix of normal random values.
        """
        rng = np.random.RandomState(PROJECTION_SEED)
        matrix = rng.randn(SDR_WIDTH, EMBEDDING_DIM).astype(np.float32)
        matrix *= 0.1  # Scale for numerical stability
        return matrix

    def encode(self, text: str) -> bytes:
        """Encode text to a 2048-bit SDR as bytes.

        Args:
            text: Input text to encode.

        Returns:
            256 bytes (2048 bits) representing the sparse distributed representation.

        Raises:
            ValueError: If text is empty.
        """
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        # Step 1: Get 384-dim embedding from BGE
        embedding = self.model.encode(text, normalize_embeddings=True)

        # Step 2: Project through LSH matrix
        projections = self.projection_matrix @ embedding  # (2048,)

        # Step 3: Select top-k bits by absolute magnitude where projection > 0
        abs_projections = np.abs(projections)
        sorted_indices = np.argsort(abs_projections)[::-1]  # Descending

        active_bits = []
        for idx in sorted_indices:
            if len(active_bits) >= TARGET_ACTIVE_BITS:
                break
            if projections[idx] > 0:
                active_bits.append(int(idx))

        # Step 4: Pack into bytes (LSB first, matching bitvec<u8, Lsb0>)
        sdr_bytes = bytearray(SDR_WIDTH // 8)  # 256 bytes
        for bit_idx in active_bits:
            byte_idx = bit_idx // 8
            bit_offset = bit_idx % 8
            sdr_bytes[byte_idx] |= (1 << bit_offset)

        return bytes(sdr_bytes)

    def encode_batch(self, texts: list[str]) -> list[bytes]:
        """Encode multiple texts at once (faster than one-by-one).

        Args:
            texts: List of input texts.

        Returns:
            List of 256-byte SDRs.
        """
        texts = [t.strip() for t in texts]
        if any(not t for t in texts):
            raise ValueError("All texts must be non-empty")

        # Batch encode embeddings
        embeddings = self.model.encode(texts, normalize_embeddings=True)

        results = []
        for embedding in embeddings:
            projections = self.projection_matrix @ embedding
            abs_projections = np.abs(projections)
            sorted_indices = np.argsort(abs_projections)[::-1]

            active_bits = []
            for idx in sorted_indices:
                if len(active_bits) >= TARGET_ACTIVE_BITS:
                    break
                if projections[idx] > 0:
                    active_bits.append(int(idx))

            sdr_bytes = bytearray(SDR_WIDTH // 8)
            for bit_idx in active_bits:
                byte_idx = bit_idx // 8
                bit_offset = bit_idx % 8
                sdr_bytes[byte_idx] |= (1 << bit_offset)

            results.append(bytes(sdr_bytes))

        return results


def hamming_distance(a: bytes, b: bytes) -> int:
    """Compute Hamming distance between two SDR byte arrays.

    Same algorithm as the Rust encoder: XOR + popcount.

    Args:
        a: First SDR as bytes.
        b: Second SDR as bytes.

    Returns:
        Number of differing bits.
    """
    assert len(a) == len(b), f"SDR lengths must match: {len(a)} vs {len(b)}"
    return sum(bin(ab ^ bb).count('1') for ab, bb in zip(a, b))


def sdr_sparsity(sdr: bytes) -> float:
    """Calculate the sparsity (fraction of active bits) of an SDR."""
    active = sum(bin(byte).count('1') for byte in sdr)
    return active / (len(sdr) * 8)


# ─── Quick self-test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading BGE model...")
    enc = SemanticEncoder()
    print("Model loaded.\n")

    # Test 1: Basic encoding
    sdr = enc.encode("The cat sat on the mat")
    print(f"SDR size: {len(sdr)} bytes ({len(sdr) * 8} bits)")
    print(f"Sparsity: {sdr_sparsity(sdr):.3f} ({sum(bin(b).count('1') for b in sdr)} active bits)")

    # Test 2: Determinism
    sdr2 = enc.encode("The cat sat on the mat")
    assert sdr == sdr2, "FAIL: Encoding not deterministic!"
    print("Determinism: PASS")

    # Test 3: Semantic similarity (THE key test)
    pairs = [
        ("The cat sat on the mat", "A feline rested on the rug"),
        ("It's raining outside", "Rain is falling outdoors"),
        ("The car is fast", "The vehicle has high speed"),
    ]

    print("\nSemantic similarity tests:")
    for a_text, b_text in pairs:
        a = enc.encode(a_text)
        b = enc.encode(b_text)
        dist = hamming_distance(a, b)
        print(f"  '{a_text}' vs '{b_text}'")
        print(f"    Hamming distance: {dist} / {SDR_WIDTH}")

    # Test 4: Dissimilarity
    unrelated = [
        ("The cat sat on the mat", "Quantum physics is complex"),
        ("I love pizza", "Space exploration is expensive"),
    ]

    print("\nDissimilarity tests:")
    for a_text, b_text in unrelated:
        a = enc.encode(a_text)
        b = enc.encode(b_text)
        dist = hamming_distance(a, b)
        print(f"  '{a_text}' vs '{b_text}'")
        print(f"    Hamming distance: {dist} / {SDR_WIDTH}")

    print("\nDone.")
