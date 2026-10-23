"""Drawing the way XP does it, to the pixel: GDI text with "Standard"
(greyscale) smoothing, the themes' "continuous" shadow (comctl32 v6's
DrawShadowText) and the 32-bit alpha images of ImageLists (comctl32).

For images with text that must come out identical to XP (the Start button),
but from the language's text: change the text and the image follows.

  font = Font(assets.font("framdit.ttf"), 19)       (or theme_font(...))
  font.extent("Iniciar")                            width in px, as GDI measures it
  draw_text(img, rect, "Iniciar", font, colour)     DT_LEFT|DT_VCENTER|DT_SINGLELINE
  draw_shadow_text(img, rect, text, font, colour, shadow_colour, dx, dy)
  draw_image(img, flag, (x, y))                     ImageList_Draw

How XP draws (measured to the pixel against captures of the Start button,
and read in comctl32.dll 6.0.2600.5512):

  * each glyph is the TrueType-hinted one at the requested size (FreeType's
    v35 interpreter does the same as XP's), advancing its whole hinted
    width, without kerning;
  * smoothing: the hinted outline is scaled up 4× and sampled at the centre
    of each subpixel: each pixel gets 0 to 16 points inside (17 levels);
  * each level n paints with the opacity (n/16)^(1/2.33), truncated:
    background + int((colour - background) · opacity); level 1 paints
    nothing (there is none in the capture), 16 is opaque;
  * the text is clipped to the rectangle (the italic "I", which reaches
    1/4 px to the left, loses that column, in the shadow too).

DrawShadowText(hdc, text, rect, colour, shadow_colour, dx, dy):
  1. a 32-bit DIB (rect + 10 px), "bottom-up", with the text at (5, 5) in
     white on black; every non-zero pixel becomes 255;
  2. each row: p[i] = (p[i+1] + p[i+2] + p[i+3] + p[i+4]) >> 2;
  3. each column, from the image's last row upwards: a = min(255,
     (p[y] + p[y-1] + ... + p[y-4]) >> 2) and the premultiplied colour
     ((c·a + 128) >> 8) + 1 in each channel (with a = 0, nothing);
  4. AlphaBlend of the DIB at (rect.left + dx - 4, rect.top + dy - 8);
  5. the text, on top, with DrawText.
That is why the "2, 2" shadow ends up centred 1.5 px to the right and 1 px
below.

ImageLists premultiply the colour the same way, ((c·a + 128) >> 8) + 1,
and draw with AlphaBlend (the "+ 1" shows: in the Start flag, the opaque
pixels come out 1 level above the bitmap).
"""
import ctypes as C
import functools

from lib import ttf

OVERSCALE = 4                    # samples per pixel in each direction
GAMMA = 2.33                     # opacity of each level (measured)
DT_VCENTER = 4


def level_alpha(n):
    """Opacity (0 to 1) with which GDI paints a pixel with n/16 coverage."""
    return 0 if n < 2 else (min(n, 16) / 16) ** (1 / GAMMA)


def _premultiply(c, a):
    """comctl32's premultiplied colour (shadows and ImageLists)."""
    return min(255, ((c * a + 128) >> 8) + 1) if a else 0


def _alpha_blend(dst, src, a):
    """GDI AlphaBlend with per-pixel alpha: src (already premultiplied) over
    dst, with the division by 255 rounded."""
    t = dst * (255 - a) + 128
    return min(255, src + ((t + (t >> 8)) >> 8))


def draw_image(img, src, xy):
    """ImageList_Draw of an RGBA image (from a 32-bit bitmap with alpha)
    at (x, y) of an RGBA image."""
    p, s = img.load(), src.load()
    for y in range(src.height):
        for x in range(src.width):
            X, Y = xy[0] + x, xy[1] + y
            r, g, b, a = s[x, y]
            if a and 0 <= X < img.width and 0 <= Y < img.height:
                d = p[X, Y]
                p[X, Y] = tuple(_alpha_blend(v, _premultiply(c, a), a)
                                for c, v in zip((r, g, b), d[:3])) + (d[3],)


# --------------------------------------------------------------------------
# FreeType (libfreetype.so.6) through ctypes: the hinted outlines
# --------------------------------------------------------------------------
class _Vec(C.Structure):
    _fields_ = [("x", C.c_long), ("y", C.c_long)]


class _Outline(C.Structure):
    _fields_ = [("n_contours", C.c_short), ("n_points", C.c_short), ("points", C.POINTER(_Vec)),
                ("tags", C.c_char_p), ("contours", C.POINTER(C.c_short)), ("flags", C.c_int)]


class _Bitmap(C.Structure):
    _fields_ = [("rows", C.c_uint), ("width", C.c_uint), ("pitch", C.c_int),
                ("buffer", C.POINTER(C.c_ubyte)), ("num_grays", C.c_ushort),
                ("pixel_mode", C.c_ubyte), ("palette_mode", C.c_ubyte), ("palette", C.c_void_p)]


class _Matrix(C.Structure):
    _fields_ = [("xx", C.c_long), ("xy", C.c_long), ("yx", C.c_long), ("yy", C.c_long)]


class _BBox(C.Structure):
    _fields_ = [("xMin", C.c_long), ("yMin", C.c_long), ("xMax", C.c_long), ("yMax", C.c_long)]


# offsets in FreeType 2.x structures on 64 bits (FT_FaceRec.glyph,
# FT_GlyphSlotRec.advance and .outline)
_FACE_GLYPH, _SLOT_ADVANCE, _SLOT_OUTLINE = 152, 128, 200
_LOAD_NO_BITMAP = 0x8
_OUTLINE_IGNORE_DROPOUTS = 0x8
_PIXEL_MODE_MONO = 1


@functools.lru_cache(None)
def _freetype():
    ft = C.CDLL("libfreetype.so.6")
    lib = C.c_void_p()
    if ft.FT_Init_FreeType(C.byref(lib)):
        raise RuntimeError("FreeType: FT_Init_FreeType")
    # XP's hinting interpreter (Windows 98/2000/XP), only in this library
    v35 = C.c_uint(35)
    ft.FT_Property_Set(lib, b"truetype", b"interpreter-version", C.byref(v35))
    return ft, lib


class Font:
    """A TrueType font at a size in px (the em height, like GDI's negative
    lfHeight)."""

    def __init__(self, path, px):
        self.path, self.px = path, px
        self.ascent, self.descent = ttf.gdi_ascent_descent(ttf.tables(path), px)
        self.height = self.ascent + self.descent
        ft, lib = _freetype()
        self._face = C.c_void_p()
        if ft.FT_New_Face(lib, path.encode(), 0, C.byref(self._face)) or \
                ft.FT_Set_Pixel_Sizes(self._face, 0, px):
            raise RuntimeError(f"FreeType: {path}")
        self._glyphs = {}

    def _load(self, ch):
        """(advance in px, hinted outline) of a glyph; the outline stays in
        FreeType's glyph slot until the next glyph."""
        ft, _lib = _freetype()
        gi = ft.FT_Get_Char_Index(self._face, ord(ch))
        if ft.FT_Load_Glyph(self._face, gi, _LOAD_NO_BITMAP):
            raise RuntimeError(f"FreeType: letra {ch!r}")
        slot = C.cast(self._face, C.POINTER(C.c_void_p))[_FACE_GLYPH // 8]
        advance = round(C.c_long.from_address(slot + _SLOT_ADVANCE).value / 64)
        return advance, _Outline.from_address(slot + _SLOT_OUTLINE)

    def advance(self, ch):
        if ch not in self._glyphs:
            self._glyphs[ch] = self._load(ch)[0]
        return self._glyphs[ch]

    def extent(self, text):
        """The width of the text (GetTextExtentPoint32): the sum of the advances."""
        return sum(self.advance(ch) for ch in text)

    def levels(self, text, x, baseline, size, clip=None):
        """{(x, y): n} — the coverage levels (1 to 16) of each pixel in an
        image of that size, the text starting at x on the baseline; only
        inside clip (x0, y0, x1, y1), if given."""
        ft, lib = _freetype()
        w, h = size
        cx0, cy0, cx1, cy1 = clip or (0, 0, w, h)
        out = {}
        pen = x
        for ch in text:
            advance, outline = self._load(ch)
            self._glyphs[ch] = advance
            # outline scaled up 4×, with y going down from the top of the image:
            # (pen, baseline) -> (pen·4, (h - baseline)·4) with y going up
            m = _Matrix(OVERSCALE << 16, 0, 0, OVERSCALE << 16)
            ft.FT_Outline_Transform(C.byref(outline), C.byref(m))
            ft.FT_Outline_Translate(C.byref(outline), C.c_long(pen * OVERSCALE * 64),
                                    C.c_long((h - baseline) * OVERSCALE * 64))
            outline.flags |= _OUTLINE_IGNORE_DROPOUTS      # only the centre counts
            box = _BBox()
            ft.FT_Outline_Get_CBox(C.byref(outline), C.byref(box))
            # (the outline's area, in whole subpixels)
            sx0, sy0 = box.xMin // 64, box.yMin // 64
            sx1, sy1 = -(-box.xMax // 64), -(-box.yMax // 64)
            bw, bh = sx1 - sx0, sy1 - sy0
            pen += advance
            if bw <= 0 or bh <= 0:
                continue
            ft.FT_Outline_Translate(C.byref(outline), C.c_long(-sx0 * 64), C.c_long(-sy0 * 64))
            pitch = (bw + 7) // 8
            buf = (C.c_ubyte * (pitch * bh))()
            bmp = _Bitmap(bh, bw, pitch, C.cast(buf, C.POINTER(C.c_ubyte)), 2, _PIXEL_MODE_MONO, 0, None)
            if ft.FT_Outline_Get_Bitmap(lib, C.byref(outline), C.byref(bmp)):
                raise RuntimeError(f"FreeType: letra {ch!r}")
            top = h * OVERSCALE - sy1          # first row of the bitmap, in subpixels from the top
            for r in range(bh):
                py = (top + r) // OVERSCALE
                row = buf[r * pitch:(r + 1) * pitch]
                for c in range(bw):
                    if row[c >> 3] & (0x80 >> (c & 7)):
                        px = (sx0 + c) // OVERSCALE
                        if cx0 <= px < cx1 and cy0 <= py < cy1:
                            out[px, py] = out.get((px, py), 0) + 1
        return out


def theme_font(spec, fonts):
    """Font from a theme's Font property ("Franklin Gothic Medium, 14,
    italic"): the size in points at 96 dpi, as GDI does (MulDiv(pt, 96, 72));
    fonts(family, bold, italic) gives the file."""
    parts = [p.strip() for p in spec.split(",")]
    family, pt = parts[0], int(parts[1])
    styles = {p.lower() for p in parts[2:]}
    return Font(fonts(family, "bold" in styles, "italic" in styles), (pt * 96 + 36) // 72)


# --------------------------------------------------------------------------
# Desenho
# --------------------------------------------------------------------------
def _layout(rect, font, flags):
    """(x, baseline) of the text in the rectangle (DT_LEFT|DT_SINGLELINE)."""
    x0, y0, _x1, y1 = rect
    top = (y0 + y1 - font.height) // 2 if flags & DT_VCENTER else y0
    return x0, top + font.ascent


def draw_text(img, rect, text, font, color, flags=DT_VCENTER):
    """DrawText in the rectangle (x0, y0, x1, y1), clipped to it, on an
    RGBA image."""
    x, baseline = _layout(rect, font, flags)
    p = img.load()
    for (px, py), n in font.levels(text, x, baseline, img.size, clip=rect).items():
        a = level_alpha(n)
        if a:
            d = p[px, py]
            p[px, py] = tuple(v + int((c - v) * a) for c, v in zip(color, d[:3])) + (d[3],)


def _shadow_dib(levels, w, h):
    """Steps 1 to 3: the shadow DIB, row by row from top to bottom, as
    (a, (r, g, b) premultiplied). levels already in DIB coordinates."""
    # (memory is "bottom-up": row 0 is the bottom one)
    mem = [[0] * w for _ in range(h)]
    for (x, y), n in levels.items():
        if level_alpha(n) and 0 <= x < w and 0 <= y < h:
            mem[h - 1 - y][x] = 255
    for row in mem:
        s = row[0] + row[1] + row[2] + row[3]
        for i in range(w - 5):
            s += row[i + 4] - row[i]
            row[i] = s >> 2
    for r in range(h - 5):
        nxt = mem[r + 1:r + 5]
        for x in range(w):
            mem[r][x] = min(255, (mem[r][x] + sum(rw[x] for rw in nxt)) >> 2)
    # (the image's top 5 rows get no vertical pass: the text starts 5 px
    # lower, so they are empty)
    return mem[::-1]


def draw_shadow_text(img, rect, text, font, color, shadow, dx, dy, flags=DT_VCENTER):
    """comctl32 v6's DrawShadowText (what uxtheme uses for
    TextShadowType = continuous): the blurred shadow and the text on top."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0 + 10, y1 - y0 + 10
    # the text in the DIB: the same DrawText, in the rectangle (5, 5, w - 5, h - 5)
    x, baseline = _layout((5, 5, w - 5, h - 5), font, flags)
    dib = _shadow_dib(font.levels(text, x, baseline, (w, h), clip=(5, 5, w - 5, h - 5)), w, h)
    p = img.load()
    ox, oy = x0 + dx - 4, y0 + dy - 8
    for v in range(h):
        for u in range(w):
            a = dib[v][u]
            X, Y = ox + u, oy + v
            if not a or not (0 <= X < img.width and 0 <= Y < img.height):
                continue
            d = p[X, Y]
            p[X, Y] = tuple(_alpha_blend(v, _premultiply(c, a), a) for c, v in zip(shadow, d[:3])) + (d[3],)
    draw_text(img, rect, text, font, color, flags)

