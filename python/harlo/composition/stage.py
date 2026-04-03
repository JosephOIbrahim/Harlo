"""MerkleStage — a composition stage backed by a Merkle tree.

Each layer added to the stage becomes a leaf in the Merkle tree.
The Merkle root summarises the entire stage in O(1) and any single-layer
update is O(log n)  (Rule 6).

Persistence: JSON files in data/stages/.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from .layer import Layer
from .merkle import MerkleTree, _sha256

STAGES_DIR = Path("data/stages")


class MerkleStage:
    """A composition stage backed by a Merkle tree."""

    def __init__(self, stage_id: str) -> None:
        self.stage_id = stage_id
        self._layers: list[Layer] = []
        self._tree: Optional[MerkleTree] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _layer_hash(layer: Layer) -> str:
        """Deterministic hash of a layer's content."""
        raw = json.dumps(layer.to_dict(), sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _rebuild_tree(self) -> None:
        """Rebuild the Merkle tree from scratch (used after bulk load)."""
        if not self._layers:
            self._tree = MerkleTree()
            return
        hashes = [self._layer_hash(layer) for layer in self._layers]
        self._tree = MerkleTree(hashes)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_layer(self, layer: Layer) -> str:
        """Add a layer and return the new Merkle root.

        Appending a layer requires a tree rebuild (we grow the leaf set).
        Individual leaf *updates* after construction are O(log n).
        """
        self._layers.append(layer)
        self._rebuild_tree()
        return self.get_merkle_root()

    def get_merkle_root(self) -> str:
        """Return the current Merkle root hash."""
        if self._tree is None:
            self._rebuild_tree()
        assert self._tree is not None
        return self._tree.get_root()

    def get_layers(self) -> list[Layer]:
        """Return all layers in insertion order."""
        return list(self._layers)

    def get_proof(self, index: int):
        """Return a Merkle proof for the layer at *index*."""
        if self._tree is None:
            self._rebuild_tree()
        assert self._tree is not None
        return self._tree.get_proof(index)

    def update_layer(self, index: int, layer: Layer) -> str:
        """Replace a layer at *index* with O(log n) Merkle update."""
        if index < 0 or index >= len(self._layers):
            raise IndexError(f"Layer index {index} out of range")
        self._layers[index] = layer
        assert self._tree is not None
        new_hash = self._layer_hash(layer)
        return self._tree.update_leaf(index, new_hash)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "merkle_root": self.get_merkle_root(),
            "layers": [layer.to_dict() for layer in self._layers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> MerkleStage:
        stage = cls(stage_id=data["stage_id"])
        for ld in data.get("layers", []):
            stage._layers.append(Layer.from_dict(ld))
        stage._rebuild_tree()
        return stage

    # ------------------------------------------------------------------
    # File persistence  (data/stages/<stage_id>.json)
    # ------------------------------------------------------------------

    def save(self) -> Path:
        """Persist the stage to a JSON file."""
        STAGES_DIR.mkdir(parents=True, exist_ok=True)
        path = STAGES_DIR / f"{self.stage_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, stage_id: str) -> MerkleStage:
        """Load a stage from its JSON file."""
        path = STAGES_DIR / f"{stage_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
