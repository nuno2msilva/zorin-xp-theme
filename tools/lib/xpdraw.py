"""Desenho como o XP o faz, ao píxel: o texto do GDI com a suavização
"Padrão" (tons de cinzento), a sombra "contínua" dos temas (DrawShadowText
do comctl32 v6) e as imagens de 32 bits com alfa das ImageList (comctl32).

Para imagens com texto que têm de sair iguais ao XP (o botão Iniciar), mas a
partir do texto da língua: muda o texto, a imagem acompanha.

  font = Font(assets.font("framdit.ttf"), 19)       (ou theme_font(...))
  font.extent("Iniciar")                            largura em px, como o GDI
  draw_text(img, rect, "Iniciar", font, cor)        DT_LEFT|DT_VCENTER|DT_SINGLELINE
  draw_shadow_text(img, rect, texto, font, cor, cor_sombra, dx, dy)
  draw_image(img, bandeira, (x, y))                 ImageList_Draw

Como o XP desenha (medido ao píxel contra capturas do botão Iniciar, e lido
no comctl32.dll 6.0.2600.5512):

  * cada letra é a do hinting TrueType ao tamanho pedido (o interpretador v35
    do FreeType faz o mesmo que o do XP), a avançar a largura inteira com
    hinting, sem kerning;
  * a suavização: o contorno com hinting é ampliado 4× e amostrado no centro
    de cada subpíxel: cada píxel fica com 0 a 16 pontos dentro (17 níveis);
  * cada nível n pinta com a opacidade (n/16)^(1/2,33), a truncar:
    fundo + int((cor - fundo) · opacidade); o nível 1 não pinta nada (na
    captura não há nenhum), o 16 é opaco;
  * o texto é cortado ao retângulo (o "I" itálico, que se estende 1/4 px
    para a esquerda, perde essa coluna, também na sombra).

DrawShadowText(hdc, texto, rect, cor, cor_sombra, dx, dy):
  1. um DIB de 32 bits (rect + 10 px), "de baixo para cima", com o texto em
     (5, 5) a branco sobre preto; cada píxel não nulo passa a 255;
  2. cada linha: p[i] = (p[i+1] + p[i+2] + p[i+3] + p[i+4]) >> 2;
  3. cada coluna, da última linha da imagem para cima: a = min(255,
     (p[y] + p[y-1] + ... + p[y-4]) >> 2) e a cor pré-multiplicada
     ((c·a + 128) >> 8) + 1 em cada canal (com a = 0, nada);
  4. AlphaBlend do DIB em (rect.left + dx - 4, rect.top + dy - 8);
  5. o texto, por cima, com DrawText.
Por isso a sombra "2, 2" fica centrada 1,5 px à direita e 1 px abaixo.

As ImageList pré-multiplicam a cor da mesma maneira, ((c·a + 128) >> 8) + 1,
e desenham com AlphaBlend (o "+ 1" vê-se: na bandeira do Iniciar, os píxeis
opacos saem 1 nível acima do bitmap).
"""
import ctypes as C
import functools

from lib import ttf

OVERSCALE = 4                    # amostras por píxel em cada direção
GAMMA = 2.33                     # opacidade de cada nível (medida)
DT_VCENTER = 4


def level_alpha(n):
    """Opacidade (0 a 1) com que o GDI pinta um píxel com n/16 de cobertura."""
    return 0 if n < 2 else (min(n, 16) / 16) ** (1 / GAMMA)


def _premultiply(c, a):
    """A cor pré-multiplicada do comctl32 (sombras e ImageList)."""
    return min(255, ((c * a + 128) >> 8) + 1) if a else 0


def _alpha_blend(dst, src, a):
    """AlphaBlend do GDI com alfa por píxel: src (já pré-multiplicada) por
    cima de dst, com a divisão por 255 arredondada."""
    t = dst * (255 - a) + 128
    return min(255, src + ((t + (t >> 8)) >> 8))


def draw_image(img, src, xy):
    """ImageList_Draw de uma imagem RGBA (de um bitmap de 32 bits com alfa)
    em (x, y) de uma imagem RGBA."""
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
# FreeType (libfreetype.so.6) por ctypes: os contornos com hinting
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


# deslocamentos nas estruturas do FreeType 2.x em 64 bits (FT_FaceRec.glyph,
# FT_GlyphSlotRec.advance e .outline)
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
    # o interpretador de hinting do XP (Windows 98/2000/XP), só nesta biblioteca
    v35 = C.c_uint(35)
    ft.FT_Property_Set(lib, b"truetype", b"interpreter-version", C.byref(v35))
    return ft, lib


class Font:
    """Uma letra TrueType num tamanho em px (a altura do em, como o lfHeight
    negativo do GDI)."""

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
        """(avanço em px, contorno com hinting) de uma letra; o contorno fica
        no glifo do FreeType até à próxima letra."""
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
        """A largura do texto (GetTextExtentPoint32): a soma dos avanços."""
        return sum(self.advance(ch) for ch in text)

    def levels(self, text, x, baseline, size, clip=None):
        """{(x, y): n} — os níveis de cobertura (1 a 16) de cada píxel numa
        imagem com esse tamanho, o texto a começar em x na linha de base;
        só dentro de clip (x0, y0, x1, y1), se houver."""
        ft, lib = _freetype()
        w, h = size
        cx0, cy0, cx1, cy1 = clip or (0, 0, w, h)
        out = {}
        pen = x
        for ch in text:
            advance, outline = self._load(ch)
            self._glyphs[ch] = advance
            # contorno ampliado 4×, com y para baixo a partir do topo da imagem:
            # (pen, baseline) -> (pen·4, (h - baseline)·4) com y para cima
            m = _Matrix(OVERSCALE << 16, 0, 0, OVERSCALE << 16)
            ft.FT_Outline_Transform(C.byref(outline), C.byref(m))
            ft.FT_Outline_Translate(C.byref(outline), C.c_long(pen * OVERSCALE * 64),
                                    C.c_long((h - baseline) * OVERSCALE * 64))
            outline.flags |= _OUTLINE_IGNORE_DROPOUTS      # só o centro conta
            box = _BBox()
            ft.FT_Outline_Get_CBox(C.byref(outline), C.byref(box))
            # (a zona do contorno, em subpíxeis inteiros)
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
            top = h * OVERSCALE - sy1          # 1.ª linha do bitmap, em subpíxeis de cima
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
    """Font de uma propriedade Font de um tema ("Franklin Gothic Medium, 14,
    italic"): o tamanho em pontos a 96 ppp, como o GDI (MulDiv(pt, 96, 72));
    fonts(família, negrito, itálico) dá o ficheiro."""
    parts = [p.strip() for p in spec.split(",")]
    family, pt = parts[0], int(parts[1])
    styles = {p.lower() for p in parts[2:]}
    return Font(fonts(family, "bold" in styles, "italic" in styles), (pt * 96 + 36) // 72)


# --------------------------------------------------------------------------
# Desenho
# --------------------------------------------------------------------------
def _layout(rect, font, flags):
    """(x, linha de base) do texto no retângulo (DT_LEFT|DT_SINGLELINE)."""
    x0, y0, _x1, y1 = rect
    top = (y0 + y1 - font.height) // 2 if flags & DT_VCENTER else y0
    return x0, top + font.ascent


def draw_text(img, rect, text, font, color, flags=DT_VCENTER):
    """DrawText no retângulo (x0, y0, x1, y1), cortado a ele, sobre uma
    imagem RGBA."""
    x, baseline = _layout(rect, font, flags)
    p = img.load()
    for (px, py), n in font.levels(text, x, baseline, img.size, clip=rect).items():
        a = level_alpha(n)
        if a:
            d = p[px, py]
            p[px, py] = tuple(v + int((c - v) * a) for c, v in zip(color, d[:3])) + (d[3],)


def _shadow_dib(levels, w, h):
    """Passos 1 a 3: o DIB da sombra, linha a linha de cima para baixo, em
    (a, (r, g, b) pré-multiplicado). levels já em coordenadas do DIB."""
    # (memória "de baixo para cima": a linha 0 é a de baixo)
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
    # (as 5 linhas de cima da imagem ficam sem a passagem vertical: o texto
    # começa 5 px abaixo, por isso estão vazias)
    return mem[::-1]


def draw_shadow_text(img, rect, text, font, color, shadow, dx, dy, flags=DT_VCENTER):
    """DrawShadowText do comctl32 v6 (o que o uxtheme usa para
    TextShadowType = continuous): a sombra desfocada e o texto por cima."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0 + 10, y1 - y0 + 10
    # o texto no DIB: o mesmo DrawText, no retângulo (5, 5, w - 5, h - 5)
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

