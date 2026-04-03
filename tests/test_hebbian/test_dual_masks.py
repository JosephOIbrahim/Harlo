"""Gate 5a: Hebbian dual masks — Patch 7 set/clear, not XOR.

Tests:
- effective_sdr = (base | strengthen) & ~weaken
- Set/clear is idempotent
- Conflict: weaken_mask wins
- Reinforcing bit already set to 1 keeps it 1 (XOR bug fix)
"""

from __future__ import annotations

from harlo.hebbian.learning import (
    SDR_LENGTH,
    activation_density,
    compute_effective_sdr,
)


class TestComputeEffectiveSdr:
    """Patch 7: (base | strengthen) & ~weaken."""

    def test_identity_no_masks(self) -> None:
        """No masks → effective = base."""
        base = [0] * SDR_LENGTH
        base[0] = 1
        base[100] = 1
        effective = compute_effective_sdr(base, [0] * SDR_LENGTH, [0] * SDR_LENGTH)
        assert effective == base

    def test_strengthen_sets_bits(self) -> None:
        """Strengthen mask sets bits that were 0 in base."""
        base = [0] * SDR_LENGTH
        strengthen = [0] * SDR_LENGTH
        strengthen[50] = 1
        effective = compute_effective_sdr(base, strengthen, [0] * SDR_LENGTH)
        assert effective[50] == 1

    def test_weaken_clears_bits(self) -> None:
        """Weaken mask clears bits that were 1 in base."""
        base = [0] * SDR_LENGTH
        base[50] = 1
        weaken = [0] * SDR_LENGTH
        weaken[50] = 1
        effective = compute_effective_sdr(base, [0] * SDR_LENGTH, weaken)
        assert effective[50] == 0

    def test_strengthen_idempotent(self) -> None:
        """Strengthening a bit already set to 1 keeps it 1."""
        base = [0] * SDR_LENGTH
        base[10] = 1  # Already set
        strengthen = [0] * SDR_LENGTH
        strengthen[10] = 1  # Reinforce
        effective = compute_effective_sdr(base, strengthen, [0] * SDR_LENGTH)
        assert effective[10] == 1  # XOR would flip to 0 — this is the Patch 7 fix

    def test_weaken_idempotent(self) -> None:
        """Weakening a bit already 0 keeps it 0."""
        base = [0] * SDR_LENGTH
        weaken = [0] * SDR_LENGTH
        weaken[10] = 1
        effective = compute_effective_sdr(base, [0] * SDR_LENGTH, weaken)
        assert effective[10] == 0

    def test_conflict_weaken_wins(self) -> None:
        """If same bit in both masks, weaken wins."""
        base = [0] * SDR_LENGTH
        strengthen = [0] * SDR_LENGTH
        weaken = [0] * SDR_LENGTH
        strengthen[20] = 1
        weaken[20] = 1  # Conflict
        effective = compute_effective_sdr(base, strengthen, weaken)
        assert effective[20] == 0  # Weaken wins

    def test_combined_operations(self) -> None:
        """Mix of strengthen and weaken on different bits."""
        base = [0] * SDR_LENGTH
        base[0] = 1
        base[1] = 1
        strengthen = [0] * SDR_LENGTH
        strengthen[2] = 1  # Set new bit
        weaken = [0] * SDR_LENGTH
        weaken[1] = 1  # Clear existing bit
        effective = compute_effective_sdr(base, strengthen, weaken)
        assert effective[0] == 1  # Unchanged
        assert effective[1] == 0  # Weakened
        assert effective[2] == 1  # Strengthened

    def test_xor_bug_demonstration(self) -> None:
        """Demonstrate why XOR is wrong: XOR(1,1) = 0, but we want 1."""
        base = [0] * SDR_LENGTH
        base[5] = 1
        # If we used XOR: base[5] XOR strengthen[5] = 1 XOR 1 = 0 (WRONG)
        # With OR: base[5] OR strengthen[5] = 1 OR 1 = 1 (CORRECT)
        strengthen = [0] * SDR_LENGTH
        strengthen[5] = 1
        effective = compute_effective_sdr(base, strengthen, [0] * SDR_LENGTH)
        assert effective[5] == 1  # Our implementation is correct


class TestActivationDensity:
    """Activation density computation."""

    def test_all_zeros(self) -> None:
        assert activation_density([0] * SDR_LENGTH) == 0.0

    def test_all_ones(self) -> None:
        assert activation_density([1] * SDR_LENGTH) == 1.0

    def test_typical_density(self) -> None:
        sdr = [0] * SDR_LENGTH
        for i in range(80):
            sdr[i] = 1
        expected = 80 / SDR_LENGTH
        assert abs(activation_density(sdr) - expected) < 1e-9
