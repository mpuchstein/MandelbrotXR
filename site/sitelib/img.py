"""Tiny image utilities: JPEG/PNG dimensions, a PNG encoder and a Mandelbrot hero render."""

from __future__ import annotations

import math
import struct
import zlib

__all__ = ["size", "encode_png", "mandelbrot_png"]

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
# SOFn markers carry the frame size; C4 (DHT), C8 (JPG) and CC (DAC) share the range but do not.
_SOF = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}
# Markers that stand alone, without a length field.
_STANDALONE = frozenset(range(0xD0, 0xD8)) | {0x01}


def size(path: str) -> tuple[int, int]:
    """Return (width, height) of a PNG or JPEG file; raise ValueError naming the file otherwise."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except (OSError, ValueError) as e:  # ValueError: e.g. a NUL byte in the path
        raise ValueError(f"{path}: cannot read image: {getattr(e, 'strerror', None) or e}") from None
    try:
        if data.startswith(_PNG_SIG):
            return _png_size(data)
        if data.startswith(b"\xff\xd8"):
            return _jpeg_size(data)
        raise ValueError("not a PNG or JPEG file")
    except (ValueError, struct.error) as e:
        raise ValueError(f"{path}: {e}") from None


def _png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or data[12:16] != b"IHDR" or struct.unpack(">I", data[8:12])[0] != 13:
        raise ValueError("corrupt PNG: missing IHDR")
    if struct.unpack(">I", data[29:33])[0] != zlib.crc32(data[12:29]):
        raise ValueError("corrupt PNG: IHDR checksum mismatch")
    w, h = struct.unpack(">II", data[16:24])
    if not (0 < w < 2**31 and 0 < h < 2**31):
        raise ValueError("corrupt PNG: dimension out of range")
    return w, h


def _jpeg_size(data: bytes) -> tuple[int, int]:
    i, n = 2, len(data)
    while True:
        if i >= n or data[i] != 0xFF:
            raise ValueError("corrupt JPEG: expected marker")
        while i < n and data[i] == 0xFF:  # fill bytes
            i += 1
        if i >= n:
            raise ValueError("corrupt JPEG: truncated")
        marker = data[i]
        i += 1
        if marker in _STANDALONE:
            continue
        if marker in (0xD8, 0xD9, 0xDA):
            raise ValueError("corrupt JPEG: no SOF marker before image data")
        if i + 2 > n:
            raise ValueError("corrupt JPEG: truncated segment")
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2 or i + seg_len > n:
            raise ValueError("corrupt JPEG: bad segment length")
        if marker in _SOF:
            if seg_len < 8:
                raise ValueError("corrupt JPEG: short SOF segment")
            h, w = struct.unpack(">HH", data[i + 3 : i + 7])
            if w == 0 or h == 0:
                raise ValueError("unsupported JPEG: zero dimension")
            return w, h
        i += seg_len


def _chunk(tag: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))


def _cost(row: bytes) -> int:
    """Sum of absolute values of the bytes read as signed (the libpng heuristic)."""
    hist = [0] * 256
    for b in row:
        hist[b] += 1
    return sum(c * (v if v < 128 else 256 - v) for v, c in enumerate(hist) if c)


def encode_png(width: int, height: int, rgb: bytes) -> bytes:
    """Encode 8-bit RGB pixels (row-major, no padding) as a deterministic PNG."""
    stride = width * 3
    if width <= 0 or height <= 0 or len(rgb) != stride * height:
        raise ValueError(f"encode_png: expected {stride * height} bytes for {width}x{height}, got {len(rgb)}")
    out = bytearray()
    prev = bytes(stride)
    for y in range(height):
        cur = rgb[y * stride : (y + 1) * stride]
        left = bytes(3) + cur[:-3]
        upleft = bytes(3) + prev[:-3]
        sub = bytes((a - b) & 0xFF for a, b in zip(cur, left))
        up = bytes((a - b) & 0xFF for a, b in zip(cur, prev))
        paeth = bytearray(stride)
        for x in range(stride):
            a, b, c = left[x], prev[x], upleft[x]
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            paeth[x] = (cur[x] - pred) & 0xFF
        candidates = (bytes(cur), sub, up, bytes(paeth))
        costs = [_cost(r) for r in candidates]
        best = costs.index(min(costs))  # ties resolve to the lowest filter type
        out.append((0, 1, 2, 4)[best])  # PNG filter types: None, Sub, Up, Paeth
        out += candidates[best]
        prev = cur
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return _PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(out), 9)) + _chunk(b"IEND", b"")


_BAILOUT2 = 256.0 * 256.0  # large radius keeps the smooth count continuous
_LOG2 = math.log(2.0)

# Palette stops (t in [0, 1], RGB): far field -> deep indigo -> teal -> warm gold at the boundary.
_DARK_STOPS = (
    (0.00, (9, 8, 22)),
    (0.30, (22, 20, 62)),
    (0.55, (34, 78, 112)),
    (0.75, (58, 150, 150)),
    (0.90, (226, 186, 104)),
    (1.00, (255, 236, 190)),
)
_DARK_INSIDE = (7, 6, 18)
_LIGHT_STOPS = (
    (0.00, (247, 245, 239)),
    (0.30, (226, 230, 236)),
    (0.55, (128, 168, 184)),
    (0.75, (40, 100, 128)),
    (0.90, (40, 34, 92)),
    (1.00, (196, 146, 52)),
)
_LIGHT_INSIDE = (30, 26, 66)


def _escape(cr: float, ci: float, max_iter: int) -> float:
    """Smooth escape count of c, or -1.0 for points judged inside the set.

    The loop is unrolled four times: one bailout test per block is safe because
    |z| <= 256 grows to at most 256**16 in four steps, and the smooth count
    n + 1 - log2(log|z|) is invariant to the extra squarings.
    """
    xr = cr - 0.25
    q = xr * xr + ci * ci
    if q * (q + xr) <= 0.25 * ci * ci or (cr + 1.0) ** 2 + ci * ci <= 0.0625:
        return -1.0  # main cardioid or period-2 bulb
    zr = zi = sr = si = 0.0  # (sr, si): Brent's saved point for periodicity checking
    lim = 16
    for n in range(4, max_iter + 4, 4):  # max_iter rounded up to a whole block
        zi, zr = (zr + zr) * zi + ci, zr * zr - zi * zi + cr
        zi, zr = (zr + zr) * zi + ci, zr * zr - zi * zi + cr
        zi, zr = (zr + zr) * zi + ci, zr * zr - zi * zi + cr
        zi, zr = (zr + zr) * zi + ci, zr * zr - zi * zi + cr
        m = zr * zr + zi * zi
        if m > _BAILOUT2:
            return max(0.0, n + 1.0 - math.log(0.5 * math.log(m)) / _LOG2)
        if abs(zr - sr) + abs(zi - si) < 1e-12:
            return -1.0
        if n == lim:
            sr, si = zr, zi
            lim += lim
    return -1.0


def _lerp_palette(stops: tuple, t: float) -> tuple[float, float, float]:
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3.0 - 2.0 * u)  # smoothstep between stops
            return tuple(a + (b - a) * u for a, b in zip(c0, c1))  # type: ignore[return-value]
    return tuple(float(v) for v in stops[-1][1])  # type: ignore[return-value]


def _sample_grid(gw: int, gh: int, x0: float, y0: float, step: float, max_iter: int) -> list[float]:
    """Smooth counts on a gw x gh grid (row-major), filling interior regions by Mariani-Silver.

    The Mandelbrot set is full, so a rectangle whose sampled border lies entirely
    inside the set is filled as inside without iterating its interior.
    """
    grid: list[float | None] = [None] * (gw * gh)
    crs = [x0 + (x + 0.5) * step for x in range(gw)]
    cis = [y0 - (y + 0.5) * step for y in range(gh)]

    def at(x: int, y: int) -> float:
        k = y * gw + x
        v = grid[k]
        if v is None:
            v = grid[k] = _escape(crs[x], cis[y], max_iter)
        return v

    stack = [(0, 0, gw - 1, gh - 1)]
    while stack:
        ax, ay, bx, by = stack.pop()
        if bx - ax < 8 or by - ay < 8:
            for y in range(ay, by + 1):
                for x in range(ax, bx + 1):
                    at(x, y)
            continue
        border_inside = all(at(x, ay) < 0.0 and at(x, by) < 0.0 for x in range(ax, bx + 1)) and all(
            at(ax, y) < 0.0 and at(bx, y) < 0.0 for y in range(ay + 1, by)
        )
        if border_inside:
            for y in range(ay + 1, by):
                row = y * gw
                grid[row + ax + 1 : row + bx] = [-1.0] * (bx - ax - 1)
            continue
        mx, my = (ax + bx) // 2, (ay + by) // 2
        stack += [(mx, my, bx, by), (ax, my, mx, by), (mx, ay, bx, my), (ax, ay, mx, my)]
    return grid  # type: ignore[return-value]


def mandelbrot_png(
    width: int,
    height: int,
    *,
    center: tuple[float, float] = (-0.74515, 0.11255),
    span: float = 0.0115,
    max_iter: int = 500,
    dark: bool = True,
) -> bytes:
    """Render a smooth-coloured Mandelbrot banner as PNG bytes.

    `span` is the width of the view in the complex plane; pixels are square.
    Each pixel averages a 2x2 grid of samples. Colour follows the normalised
    log of the smooth escape count, so detail near the boundary glows gold.
    """
    if width <= 0 or height <= 0:
        raise ValueError("mandelbrot_png: width and height must be positive")
    if max_iter < 1 or not (0.0 < span < math.inf) or not all(map(math.isfinite, center)):
        raise ValueError("mandelbrot_png: need max_iter >= 1, a finite span > 0 and a finite center")
    stops, inside = (_DARK_STOPS, _DARK_INSIDE) if dark else (_LIGHT_STOPS, _LIGHT_INSIDE)
    gw, gh = 2 * width, 2 * height
    step = span / gw
    grid = _sample_grid(gw, gh, center[0] - span / 2.0, center[1] + step * gh / 2.0, step, max_iter)

    lut_n = 1024
    lut = [_lerp_palette(stops, k / (lut_n - 1)) for k in range(lut_n)]
    log_max = math.log(max_iter + 2.0)
    colours = []
    for nu in grid:
        if nu < 0.0:
            colours.append(inside)
        else:
            t = math.log(nu + 1.0) / log_max
            colours.append(lut[min(lut_n - 1, int(t * t * (lut_n - 1)))])

    out = bytearray(width * height * 3)
    pos = 0
    for py in range(height):
        top = 2 * py * gw
        bot = top + gw
        for px in range(width):
            k = 2 * px
            c0, c1, c2, c3 = colours[top + k], colours[top + k + 1], colours[bot + k], colours[bot + k + 1]
            for ch in range(3):
                out[pos + ch] = int((c0[ch] + c1[ch] + c2[ch] + c3[ch]) * 0.25 + 0.5)
            pos += 3
    return encode_png(width, height, bytes(out))
