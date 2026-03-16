"""Patch 9: Hex SDR encoding — lossless round-trip tests.

2048-bit arrays serialize as 512-char hex strings and round-trip without loss.
"""

from __future__ import annotations

import random

import pytest

from cognitive_twin.usd_lite.hex_sdr import (
    HEX_LENGTH,
    SDR_LENGTH,
    hex_to_sdr,
    sdr_to_hex,
)


class TestSdrToHex:
    """Tests for sdr_to_hex."""

    def test_all_zeros(self) -> None:
        sdr = [0] * SDR_LENGTH
        result = sdr_to_hex(sdr)
        assert len(result) == HEX_LENGTH
        assert result == "0" * HEX_LENGTH

    def test_all_ones(self) -> None:
        sdr = [1] * SDR_LENGTH
        result = sdr_to_hex(sdr)
        assert len(result) == HEX_LENGTH
        assert result == "f" * HEX_LENGTH

    def test_known_nibble(self) -> None:
        """Test a known 4-bit pattern: [1, 0, 1, 0] = 0b1010 = 0xa."""
        sdr = [0] * SDR_LENGTH
        sdr[0], sdr[1], sdr[2], sdr[3] = 1, 0, 1, 0
        result = sdr_to_hex(sdr)
        assert result[0] == "a"
        assert result[1:] == "0" * (HEX_LENGTH - 1)

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="2048"):
            sdr_to_hex([0] * 100)

    def test_non_binary_raises(self) -> None:
        sdr = [0] * SDR_LENGTH
        sdr[10] = 2
        with pytest.raises(ValueError, match="non-binary"):
            sdr_to_hex(sdr)


class TestHexToSdr:
    """Tests for hex_to_sdr."""

    def test_all_zeros(self) -> None:
        result = hex_to_sdr("0" * HEX_LENGTH)
        assert result == [0] * SDR_LENGTH

    def test_all_ones(self) -> None:
        result = hex_to_sdr("f" * HEX_LENGTH)
        assert result == [1] * SDR_LENGTH

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="512"):
            hex_to_sdr("abc")

    def test_non_hex_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            hex_to_sdr("g" + "0" * (HEX_LENGTH - 1))


class TestRoundTrip:
    """Round-trip: hex_to_sdr(sdr_to_hex(sdr)) == sdr."""

    def test_all_zeros_roundtrip(self) -> None:
        sdr = [0] * SDR_LENGTH
        assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_all_ones_roundtrip(self) -> None:
        sdr = [1] * SDR_LENGTH
        assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_random_roundtrip(self) -> None:
        rng = random.Random(42)
        sdr = [rng.randint(0, 1) for _ in range(SDR_LENGTH)]
        assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_sparse_roundtrip(self) -> None:
        """Typical SDR: ~3-5% density."""
        rng = random.Random(99)
        sdr = [0] * SDR_LENGTH
        for idx in rng.sample(range(SDR_LENGTH), 80):  # ~3.9% density
            sdr[idx] = 1
        assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_single_bit_roundtrip(self) -> None:
        """Every single-bit SDR round-trips."""
        for pos in [0, 1, 3, 4, 7, 100, 1023, 2047]:
            sdr = [0] * SDR_LENGTH
            sdr[pos] = 1
            assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_alternating_roundtrip(self) -> None:
        sdr = [i % 2 for i in range(SDR_LENGTH)]
        assert hex_to_sdr(sdr_to_hex(sdr)) == sdr

    def test_uppercase_hex_accepted(self) -> None:
        """hex_to_sdr should accept uppercase hex."""
        sdr = [1, 0, 1, 0] + [0] * (SDR_LENGTH - 4)
        hex_str = sdr_to_hex(sdr).upper()
        assert hex_to_sdr(hex_str) == sdr
