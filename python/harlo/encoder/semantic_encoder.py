"""
Semantic SDR encoder using sentence-transformers + LSH projection.

Produces the same 2048-bit SDR format as the Rust lexical encoder,
so hamming_distance works identically on both.

Pipeline:
    text → sentence-transformers → 384-dim float embedding
    → LSH projection → top-k bit selection → 2048-bit SDR (bytes)
"""

import numpy as np
from typing import Optional

# Lean-bundle degrade path: sentence_transformers is deliberately EXCLUDED
# from the v0.1.x bundle (see setup_py2app.py excludes). Import optionally
# so the encoder package loads cleanly; SemanticEncoder.__init__ raises a
# clear ImportError if instantiation is attempted without the dep. Callers
# should route to the Rust lexical encoder (harlo.hippocampus.py_recall)
# on ImportError as the architected degrade path.
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]

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

        Raises:
            ImportError: If sentence_transformers is not installed (lean-bundle
                degrade — callers should route to the Rust lexical encoder).
        """
        if SentenceTransformer is None:
            raise ImportError(
                "sentence_transformers is not installed; the lean bundle "
                "excludes the ML stack. Degrade path: use the Rust lexical "
                "encoder via harlo.hippocampus.py_recall / py_store_trace."
            )
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

    def _embedding_to_sdr(self, embedding: np.ndarray) -> bytes:
        """Convert one 384-dim float embedding to a 256-byte SDR blob.

        Shared projection → abs/top-k → bit-pack pipeline so encode() and
        encode_batch() produce byte-identical output.

        Args:
            embedding: 384-dim float vector (L2-normalized).

        Returns:
            256 bytes (2048 bits) representing the sparse distributed representation.
        """
        # Project through LSH matrix
        projections = self.projection_matrix @ embedding  # (2048,)

        # Select top-k bits by absolute magnitude where projection > 0
        abs_projections = np.abs(projections)
        sorted_indices = np.argsort(abs_projections)[::-1]  # Descending

        active_bits = []
        for idx in sorted_indices:
            if len(active_bits) >= TARGET_ACTIVE_BITS:
                break
            if projections[idx] > 0:
                active_bits.append(int(idx))

        # Pack into bytes (LSB first, matching bitvec<u8, Lsb0>)
        sdr_bytes = bytearray(SDR_WIDTH // 8)  # 256 bytes
        for bit_idx in active_bits:
            byte_idx = bit_idx // 8
            bit_offset = bit_idx % 8
            sdr_bytes[byte_idx] |= (1 << bit_offset)

        return bytes(sdr_bytes)

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

        embedding = self.model.encode(text, normalize_embeddings=True)
        return self._embedding_to_sdr(embedding)

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

        return [self._embedding_to_sdr(embedding) for embedding in embeddings]


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
