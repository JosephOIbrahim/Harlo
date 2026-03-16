"""Hex encoding/decoding for 2048-bit SDR arrays.

Patch 9: 2048-bit integer arrays serialize as dense 512-character hex strings
instead of text arrays of 2048 integers.  A text array consumes ~6KB per trace;
hex packs to 512 bytes.
"""

from __future__ import annotations

SDR_LENGTH = 2048
HEX_LENGTH = SDR_LENGTH // 4  # 512


def sdr_to_hex(sdr: list[int]) -> str:
    """Convert a 2048-element boolean int array to a 512-char hex string.

    Each element must be 0 or 1.  Groups of 4 bits map to 1 hex char,
    big-endian bit ordering within each nibble: [b3, b2, b1, b0].

    Raises ValueError if len(sdr) != 2048 or elements not in {0, 1}.
    """
    if len(sdr) != SDR_LENGTH:
        raise ValueError(
            f"SDR must have exactly {SDR_LENGTH} elements, got {len(sdr)}"
        )
    chars: list[str] = []
    for i in range(0, SDR_LENGTH, 4):
        b3, b2, b1, b0 = sdr[i], sdr[i + 1], sdr[i + 2], sdr[i + 3]
        if not all(v in (0, 1) for v in (b3, b2, b1, b0)):
            raise ValueError(
                f"SDR elements must be 0 or 1, got non-binary value at index {i}..{i+3}"
            )
        nibble = (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
        chars.append(f"{nibble:x}")
    return "".join(chars)


def hex_to_sdr(hex_str: str) -> list[int]:
    """Convert a 512-char hex string back to a 2048-element boolean int array.

    Raises ValueError if len(hex_str) != 512 or contains non-hex chars.
    """
    if len(hex_str) != HEX_LENGTH:
        raise ValueError(
            f"Hex string must be exactly {HEX_LENGTH} chars, got {len(hex_str)}"
        )
    sdr: list[int] = []
    for ch in hex_str:
        try:
            nibble = int(ch, 16)
        except ValueError:
            raise ValueError(f"Invalid hex character: {ch!r}")
        sdr.append((nibble >> 3) & 1)
        sdr.append((nibble >> 2) & 1)
        sdr.append((nibble >> 1) & 1)
        sdr.append(nibble & 1)
    return sdr
