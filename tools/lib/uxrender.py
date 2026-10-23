"""Reimplementation of uxtheme's background drawing (DrawThemeBackground).

Used to pre-draw fixed-size elements exactly as XP would draw them (4 px
frames, caption buttons, scrollbar arrows with the centred glyph, etc.).
"""
from PIL import Image


def _axis(src_len, dst_len, m0, m1):
    """Segments (src0, src1, dst0, dst1) on one axis, the uxtheme way.

    When the destination is smaller than the sum of the margins, uxtheme
    shrinks the margins proportionally and the centre disappears.
    """
    if dst_len >= m0 + m1:
        return [(0, m0, 0, m0, False),
                (m0, src_len - m1, m0, dst_len - m1, True),
                (src_len - m1, src_len, dst_len - m1, dst_len, False)]
    if m0 + m1 == 0:
        return [(0, src_len, 0, dst_len, True)]
    d0 = dst_len * m0 // (m0 + m1)
    # shrunk margins: always stretched (never tiled)
    return [(0, m0, 0, d0, False), (src_len - m1, src_len, d0, dst_len, False)]


def gdi_stretch(img, w, h):
    """StretchBlt (COLORONCOLOR) as in XP.

    Stretching: source = floor((i + 0.5)·s/d)  (real title bar: 3 -> 861 and 3 -> 4)
    Shrinking: source = floor(i·s/d + 0.5)  (real progress bar: 12 -> 7)
    """
    if img.size == (w, h):
        return img.copy()

    def axis(s, d):
        if d < s:
            return [min(s - 1, int(i * s / d + 0.5)) for i in range(d)]
        return [min(s - 1, int((i + 0.5) * s / d)) for i in range(d)]
    xs = axis(img.width, w)
    ys = axis(img.height, h)
    src = img.load()
    out = Image.new("RGBA", (w, h))
    dst = out.load()
    for y, sy in enumerate(ys):
        for x, sx in enumerate(xs):
            dst[x, y] = src[sx, sy]
    return out


def _fit(piece, length, tiled, horizontal):
    w, h = piece.size
    cur = w if horizontal else h
    if cur == length:
        return piece
    if not tiled:
        return gdi_stretch(piece, length, h) if horizontal else gdi_stretch(piece, w, length)
    out = Image.new("RGBA", (length, h) if horizontal else (w, length), (0, 0, 0, 0))
    for p in range(0, length, cur):
        out.paste(piece, (p, 0) if horizontal else (0, p))
    return out


def render(src, w, h, margins=(0, 0, 0, 0), tile=False):
    """src: the image of one state; margins: (left, right, top, bottom) as in the INI."""
    l, r, t, b = margins
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for sx0, sx1, dx0, dx1, tx in _axis(src.width, w, l, r):
        for sy0, sy1, dy0, dy1, ty in _axis(src.height, h, t, b):
            if sx1 <= sx0 or sy1 <= sy0 or dx1 <= dx0 or dy1 <= dy0:
                continue
            piece = src.crop((sx0, sy0, sx1, sy1))
            dw, dh = dx1 - dx0, dy1 - dy0
            # each axis: the centre in Tile mode repeats (or is cut); the rest stretches
            piece = _fit(piece, dw, tile and tx, horizontal=True)
            piece = _fit(piece, dh, tile and ty, horizontal=False)
            out.alpha_composite(piece, (dx0, dy0))
    return out


def center(base, glyph, offset=(0, 0)):
    """Composes a centred glyph (GlyphType=ImageGlyph, default alignment)."""
    out = base.copy()
    x = (base.width - glyph.width) // 2 + offset[0]
    y = (base.height - glyph.height) // 2 + offset[1]
    out.alpha_composite(glyph, (x, y))
    return out
