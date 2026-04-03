"""ONNX Runtime encoder for BAAI/bge-small-en-v1.5.

Produces SDR blobs matching SemanticEncoder's output within the
fidelity gate (Hamming distance correlation >= 0.95).
Same LSH projection matrix (seed=42, shape 2048x384).
Model loads ONCE at __init__, not per-call.

Uses transformers.AutoTokenizer for tokenization parity with
sentence-transformers (the reference encoder).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

# Match SemanticEncoder constants exactly
SDR_WIDTH = 2048
TARGET_ACTIVE_BITS = 80
PROJECTION_SEED = 42
EMBEDDING_DIM = 384

# Model name for tokenizer (must match SemanticEncoder's model)
MODEL_NAME = "BAAI/bge-small-en-v1.5"


class OnnxEncoder:
    """ONNX Runtime encoder for BAAI/bge-small-en-v1.5.

    Produces SDR blobs compatible with SemanticEncoder.
    Uses the same LSH projection matrix (seed=42) for bit-level compatibility.
    Uses AutoTokenizer for identical tokenization with sentence-transformers.
    Model loads ONCE at instantiation, not per-call.
    """

    def __init__(self, model_path: str) -> None:
        """Initialize ONNX encoder.

        Args:
            model_path: Path to the .onnx model file.

        Raises:
            FileNotFoundError: If model_path does not exist.
            RuntimeError: If ONNX Runtime fails to load the model.
        """
        model_path = str(model_path)
        if not Path(model_path).exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        self._session = ort.InferenceSession(model_path)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self._projection_matrix = self._create_projection_matrix()

        logger.info("OnnxEncoder loaded: %s", model_path)

    def _create_projection_matrix(self) -> np.ndarray:
        """Create LSH projection matrix (2048 x 384).

        Uses np.random.RandomState(PROJECTION_SEED) for determinism.
        MUST match SemanticEncoder._create_projection_matrix() exactly.
        """
        rng = np.random.RandomState(PROJECTION_SEED)
        matrix = rng.randn(SDR_WIDTH, EMBEDDING_DIM).astype(np.float32)
        matrix *= 0.1
        return matrix

    def encode(self, text: str) -> bytes:
        """Encode text to 256-byte SDR blob.

        Args:
            text: Input text string.

        Returns:
            256-byte SDR blob (2048-bit, ~80 active bits).

        Raises:
            ValueError: If text is empty.
        """
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        results = self.encode_batch([text])
        return results[0]

    def encode_batch(self, texts: list[str]) -> list[bytes]:
        """Batch-encode texts to SDR blobs.

        Args:
            texts: List of input text strings.

        Returns:
            List of 256-byte SDR blobs.

        Raises:
            ValueError: If any text is empty.
        """
        texts = [t.strip() for t in texts]
        if any(not t for t in texts):
            raise ValueError("All texts must be non-empty")

        # Tokenize using AutoTokenizer (matches sentence-transformers)
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        input_ids = encoded["input_ids"].astype(np.int64)
        attention_mask = encoded["attention_mask"].astype(np.int64)
        token_type_ids = encoded.get(
            "token_type_ids",
            np.zeros_like(input_ids),
        ).astype(np.int64)

        # ONNX inference
        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )
        last_hidden_state = outputs[0]  # [batch, seq, 384]

        # CLS token pooling + L2 normalize (matching sentence-transformers)
        # BGE-small-en-v1.5 uses pooling_mode_cls_token=True, NOT mean pooling
        embeddings = last_hidden_state[:, 0, :]  # [CLS] token is position 0

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
        embeddings = embeddings / norms

        # Project to SDRs
        results = []
        for embedding in embeddings:
            sdr_blob = self._embedding_to_sdr(embedding)
            results.append(sdr_blob)

        return results

    def _embedding_to_sdr(self, embedding: np.ndarray) -> bytes:
        """Convert 384-dim float embedding to 256-byte SDR blob.

        Args:
            embedding: 384-dim float32 vector (L2-normalized).

        Returns:
            256-byte SDR blob.
        """
        projections = self._projection_matrix @ embedding

        abs_projections = np.abs(projections)
        sorted_indices = np.argsort(abs_projections)[::-1]

        active_bits: list[int] = []
        for idx in sorted_indices:
            if len(active_bits) >= TARGET_ACTIVE_BITS:
                break
            if projections[idx] > 0:
                active_bits.append(int(idx))

        sdr_bytes = bytearray(SDR_WIDTH // 8)
        for bit_idx in active_bits:
            byte_idx = bit_idx // 8
            bit_offset = bit_idx % 8
            sdr_bytes[byte_idx] |= 1 << bit_offset

        return bytes(sdr_bytes)
