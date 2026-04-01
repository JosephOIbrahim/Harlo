"""Hebbian neuroplasticity — co-activation, dual-mask SDR evolution,
episodic reconstruction, and Elenchus training data pipeline.
"""

from .learning import (
    HebbianUpdate,
    activation_density,
    apply_hebbian_strengthening,
    compute_effective_sdr,
    record_co_activation,
    record_competition,
)
from .reconstruction import (
    ReconstructedEpisode,
    apply_reconsolidation_boost,
    get_reconstruction_threshold,
    needs_reconstruction,
    reconstruct_episode,
)
from .training_data import (
    get_row_count,
    record_verification,
)

__all__ = [
    "HebbianUpdate",
    "ReconstructedEpisode",
    "activation_density",
    "apply_hebbian_strengthening",
    "apply_reconsolidation_boost",
    "compute_effective_sdr",
    "get_reconstruction_threshold",
    "get_row_count",
    "needs_reconstruction",
    "record_co_activation",
    "record_competition",
    "record_verification",
    "reconstruct_episode",
]
