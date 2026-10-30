"""QR Code Model 2 encoder (ISO/IEC 18004), byte mode, versions 1-40, stdlib only."""

from __future__ import annotations

import re

__all__ = ["matrix", "svg"]

_ECC_ORDER = "LMQH"
_FORMAT_BITS = {"L": 1, "M": 0, "Q": 3, "H": 2}

# Per ECC level (L, M, Q, H), indexed by version (index 0 unused).
_ECC_PER_BLOCK = (
    (0, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
     28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
     26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    (0, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
     28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (0, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
     30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
)
_NUM_BLOCKS = (
    (0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
     8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    (0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
     17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    (0, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
     23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    (0, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
     25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
)

# GF(256) with primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D).
_EXP = [0] * 512
_LOG = [0] * 256
_v = 1
for _i in range(255):
    _EXP[_i] = _v
    _LOG[_v] = _i
    _v <<= 1
    if _v & 0x100:
        _v ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]
del _v, _i


def _gf_mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(degree: int) -> list[int]:
    """Monic generator polynomial prod(x - a^i), i < degree, highest term dropped."""
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        for j, c in enumerate(poly):
            nxt[j] ^= c
            nxt[j + 1] ^= _gf_mul(c, _EXP[i])
        poly = nxt
    return poly[1:]


def _rs_remainder(data: list[int], gen: list[int]) -> list[int]:
    rem = [0] * len(gen)
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        if factor:
            for j, g in enumerate(gen):
                rem[j] ^= _gf_mul(g, factor)
    return rem


def _raw_data_modules(version: int) -> int:
    """Modules available for data + ECC (incl. remainder bits) in a symbol."""
    result = (16 * version + 128) * version + 64
    if version >= 2:
        n = version // 7 + 2
        result -= (25 * n - 10) * n - 55
        if version >= 7:
            result -= 36
    return result


def _data_codewords(version: int, level: int) -> int:
    return (_raw_data_modules(version) // 8
            - _ECC_PER_BLOCK[level][version] * _NUM_BLOCKS[level][version])


def _alignment_positions(version: int) -> list[int]:
    if version == 1:
        return []
    n = version // 7 + 2
    step = (version * 8 + n * 3 + 5) // (n * 4 - 4) * 2
    size = version * 4 + 17
    return [6] + sorted(size - 7 - i * step for i in range(n - 1))


def _encode_codewords(payload: bytes, version: int, level: int) -> list[int]:
    """Byte-mode bitstream, padding, RS blocks and interleaving."""
    cc_bits = 8 if version <= 9 else 16
    capacity = _data_codewords(version, level) * 8
    bits: list[int] = []

    def put(value: int, length: int) -> None:
        bits.extend((value >> i) & 1 for i in range(length - 1, -1, -1))

    put(0b0100, 4)
    put(len(payload), cc_bits)
    for b in payload:
        put(b, 8)
    put(0, min(4, capacity - len(bits)))
    put(0, -len(bits) % 8)
    data = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(data) < capacity // 8:
        data.append(pad)
        pad ^= 0xEC ^ 0x11

    num_blocks = _NUM_BLOCKS[level][version]
    ecc_len = _ECC_PER_BLOCK[level][version]
    raw = _raw_data_modules(version) // 8
    num_short = num_blocks - raw % num_blocks
    short_len = raw // num_blocks - ecc_len
    gen = _rs_generator(ecc_len)
    blocks: list[list[int]] = []
    eccs: list[list[int]] = []
    pos = 0
    for i in range(num_blocks):
        n = short_len + (0 if i < num_short else 1)
        block = data[pos:pos + n]
        pos += n
        blocks.append(block)
        eccs.append(_rs_remainder(block, gen))
    out = [b[i] for i in range(short_len + 1) for b in blocks if i < len(b)]
    out += [e[i] for i in range(ecc_len) for e in eccs]
    return out


def _bch_format(level: str, mask: int) -> int:
    data = _FORMAT_BITS[level] << 3 | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return (data << 10 | rem) ^ 0x5412


def _bch_version(version: int) -> int:
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
    return version << 12 | rem


class _Symbol:
    """Mutable module grid; grid[y][x], True = dark."""

    def __init__(self, version: int) -> None:
        self.version = version
        self.size = size = version * 4 + 17
        self.grid = [[False] * size for _ in range(size)]
        self.func = [[False] * size for _ in range(size)]
        self._draw_function_patterns()

    def _set(self, x: int, y: int, dark: bool) -> None:
        self.grid[y][x] = dark
        self.func[y][x] = True

    def _draw_function_patterns(self) -> None:
        size = self.size
        for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < size and 0 <= y < size:
                        self._set(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = _alignment_positions(self.version)
        last = len(pos) - 1
        for i, ay in enumerate(pos):
            for j, ax in enumerate(pos):
                if (i, j) in ((0, 0), (0, last), (last, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
        # Reserve format/version areas as light; they are written after mask selection.
        for i in range(9):
            self._set(8, i, False)
            self._set(i, 8, False)
        for i in range(8):
            self._set(size - 1 - i, 8, False)
            self._set(8, size - 1 - i, False)
        if self.version >= 7:
            for i in range(18):
                a, b = size - 11 + i % 3, i // 3
                self._set(a, b, False)
                self._set(b, a, False)
        for i in range(8, size - 8):  # timing; overrides the reserved cells (6, 8), (8, 6)
            self._set(6, i, i % 2 == 0)
            self._set(i, 6, i % 2 == 0)

    def draw_version(self) -> None:
        if self.version < 7:
            return
        bits = _bch_version(self.version)
        for i in range(18):
            dark = (bits >> i) & 1 == 1
            a, b = self.size - 11 + i % 3, i // 3
            self._set(a, b, dark)
            self._set(b, a, dark)

    def draw_format(self, level: str, mask: int) -> None:
        bits = _bch_format(level, mask)
        size = self.size
        bit = [(bits >> i) & 1 == 1 for i in range(15)]
        for i in range(6):
            self._set(8, i, bit[i])
        self._set(8, 7, bit[6])
        self._set(8, 8, bit[7])
        self._set(7, 8, bit[8])
        for i in range(9, 15):
            self._set(14 - i, 8, bit[i])
        for i in range(8):
            self._set(size - 1 - i, 8, bit[i])
        for i in range(8, 15):
            self._set(8, size - 15 + i, bit[i])
        self._set(8, size - 8, True)

    def place_data(self, codewords: list[int]) -> None:
        size = self.size
        total = len(codewords) * 8
        i = 0
        right = size - 1
        while right >= 1:
            if right == 6:
                right = 5
            upward = (right + 1) & 2 == 0
            for vert in range(size):
                y = size - 1 - vert if upward else vert
                for x in (right, right - 1):
                    if not self.func[y][x] and i < total:
                        self.grid[y][x] = (codewords[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def apply_mask(self, mask: int) -> None:
        cond = _MASKS[mask]
        for y in range(self.size):
            row, frow = self.grid[y], self.func[y]
            for x in range(self.size):
                if not frow[x] and cond(x, y):
                    row[x] = not row[x]


_MASKS = (
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


def _line_penalty(line: str) -> int:
    """Rules 1 (runs >= 5) and 3 (1:1:3:1:1 finder-like) for one row or column."""
    score = 0
    run = 1
    for a, b in zip(line, line[1:]):
        if a == b:
            run += 1
        else:
            if run >= 5:
                score += run - 2
            run = 1
    if run >= 5:
        score += run - 2
    # Each finder-like core counts once; scanning resumes after a counted core.
    padded = "0000" + line + "0000"
    idx = padded.find("1011101")
    while idx != -1:
        if padded[idx - 4:idx] == "0000" or padded[idx + 7:idx + 11] == "0000":
            score += 40
            idx = padded.find("1011101", idx + 7)
        else:
            idx = padded.find("1011101", idx + 1)
    return score


def _penalty(grid: list[list[bool]]) -> int:
    size = len(grid)
    rows = ["".join("1" if m else "0" for m in row) for row in grid]
    cols = ["".join(r[x] for r in rows) for x in range(size)]
    score = sum(_line_penalty(line) for line in rows) + sum(_line_penalty(c) for c in cols)
    for r0, r1 in zip(rows, rows[1:]):
        for x in range(size - 1):
            if r0[x] == r0[x + 1] == r1[x] == r1[x + 1]:
                score += 3
    dark = sum(r.count("1") for r in rows)
    total = size * size
    score += abs(dark * 20 - total * 10) // total * 10  # 10 per full 5 % off 50 %
    return score


def _encode(data: str, ecc: str = "M", mask: int | None = None) -> list[list[bool]]:
    """Build the symbol; `mask` forces a mask pattern (0-7) instead of auto-selection."""
    level_name = ecc.upper() if isinstance(ecc, str) else ""
    if len(level_name) != 1 or level_name not in _ECC_ORDER:
        raise ValueError(f"invalid ECC level {ecc!r}; expected one of L, M, Q, H")
    if mask is not None and mask not in range(8):
        raise ValueError(f"invalid mask {mask!r}; expected 0-7")
    level = _ECC_ORDER.index(level_name)
    payload = data.encode("utf-8")
    for version in range(1, 41):
        needed = 4 + (8 if version <= 9 else 16) + 8 * len(payload)
        if needed <= _data_codewords(version, level) * 8:
            break
    else:
        raise ValueError(f"data too long for a QR code at ECC level {level_name}: "
                         f"{len(payload)} bytes")
    symbol = _Symbol(version)
    symbol.place_data(_encode_codewords(payload, version, level))
    if mask is None:
        best: tuple[int, int] | None = None
        # ISO/IEC 18004 7.1 steps 6-7: masks are scored before format/version info exist.
        for m in range(8):
            symbol.apply_mask(m)
            score = _penalty(symbol.grid)
            if best is None or score < best[0]:
                best = (score, m)
            symbol.apply_mask(m)  # XOR undo
        mask = best[1]
    symbol.apply_mask(mask)
    symbol.draw_format(level_name, mask)
    symbol.draw_version()
    return [row[:] for row in symbol.grid]


def matrix(data: str, ecc: str = "M") -> list[list[bool]]:
    """Return the QR module matrix for `data` (UTF-8 byte mode); True = dark, no quiet zone."""
    return _encode(data, ecc)


_XML_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def _xml_escape(text: str) -> str:
    """Escape text content, dropping characters XML 1.0 does not allow."""
    text = _XML_INVALID.sub("", text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(data: str, *, ecc: str = "M", border: int = 4, title: str | None = None) -> str:
    """Return a standalone inline <svg> of the QR code, sized by CSS via its viewBox."""
    if border < 0:
        raise ValueError("border must be non-negative")
    grid = matrix(data, ecc)
    dim = len(grid) + 2 * border
    parts: list[str] = []
    for y, row in enumerate(grid):
        x = 0
        n = len(row)
        while x < n:
            if row[x]:
                start = x
                while x < n and row[x]:
                    x += 1
                run = x - start
                parts.append(f"M{start + border} {y + border}h{run}v1h-{run}z")
            else:
                x += 1
    label = _xml_escape(data if title is None else title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" '
        f'shape-rendering="crispEdges" role="img">'
        f"<title>{label}</title>"
        f'<rect width="{dim}" height="{dim}" fill="#fff"/>'
        f'<path fill="#000" d="{"".join(parts)}"/>'
        f"</svg>"
    )
