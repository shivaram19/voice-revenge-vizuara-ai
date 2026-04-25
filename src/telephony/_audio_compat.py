"""
Audio compatibility layer for Python 3.13+
audioop was removed in Python 3.13 (PEP 594).
Ref: ITU-T G.711 (1972) [^38].
"""

import struct

# μ-law companding lookup tables
_MULAW_BIAS = 33
_MULAW_CLIP = 32635
_MULAW_MAX = 0x7F7B


def _ulaw2lin_sample(u: int) -> int:
    """Decode single μ-law byte to 16-bit signed linear PCM."""
    u = ~u & 0xFF
    sign = (u & 0x80) >> 7
    exponent = (u & 0x70) >> 4
    mantissa = u & 0x0F
    value = ((mantissa << 3) + _MULAW_BIAS) << exponent
    value -= _MULAW_BIAS
    return -value if sign else value


def _lin2ulaw_sample(s: int) -> int:
    """Encode single 16-bit signed linear PCM to μ-law byte."""
    if s < 0:
        sign = 0x80
        s = -s
    else:
        sign = 0x00

    s = min(s, _MULAW_CLIP)
    s += _MULAW_BIAS

    if s <= 0x7F:
        exponent = 0
        mantissa = (s >> 3) & 0x0F
    elif s <= 0xFF:
        exponent = 1
        mantissa = (s >> 4) & 0x0F
    elif s <= 0x1FF:
        exponent = 2
        mantissa = (s >> 5) & 0x0F
    elif s <= 0x3FF:
        exponent = 3
        mantissa = (s >> 6) & 0x0F
    elif s <= 0x7FF:
        exponent = 4
        mantissa = (s >> 7) & 0x0F
    elif s <= 0xFFF:
        exponent = 5
        mantissa = (s >> 8) & 0x0F
    elif s <= 0x1FFF:
        exponent = 6
        mantissa = (s >> 9) & 0x0F
    else:
        exponent = 7
        mantissa = (s >> 10) & 0x0F

    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def ulaw2lin(data: bytes, width: int) -> bytes:
    """Convert μ-law bytes to linear PCM."""
    if width == 2:
        return b"".join(struct.pack("<h", _ulaw2lin_sample(b)) for b in data)
    raise ValueError(f"Unsupported width: {width}")


def lin2ulaw(data: bytes, width: int) -> bytes:
    """Convert linear PCM to μ-law bytes."""
    if width == 2:
        samples = struct.unpack(f"<{len(data)//2}h", data)
        return bytes(_lin2ulaw_sample(s) for s in samples)
    raise ValueError(f"Unsupported width: {width}")


def ratecv(data: bytes, width: int, nchannels: int, inrate: int, outrate: int, state):
    """Simple linear-interpolation resampling."""
    if width != 2:
        raise ValueError(f"Unsupported width: {width}")
    if nchannels != 1:
        raise ValueError("Only mono supported")

    samples = list(struct.unpack(f"<{len(data)//width}h", data))
    if not samples:
        return b"", state

    ratio = inrate / outrate
    out_len = int(len(samples) / ratio)
    result = []

    for i in range(out_len):
        src_idx = i * ratio
        idx_floor = int(src_idx)
        idx_ceil = min(idx_floor + 1, len(samples) - 1)
        frac = src_idx - idx_floor
        val = samples[idx_floor] * (1 - frac) + samples[idx_ceil] * frac
        result.append(int(val))

    return struct.pack(f"<{len(result)}h", *result), state


# References
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
