#!/usr/bin/env python3
"""Fonte "de píxeis" com o texto do XP: cada letra é o desenho que o GDI do
XP faz da Tahoma a um tamanho fixo (hinting TrueType v35, sem suavização)
convertido em quadrados de 1 px, e avança a largura inteira do XP.

Para programas que não usam as larguras ajustadas das letras (o Firefox/Zen
usa as da fonte sem hinting e as letras ficam com espaços irregulares — "Fav
oritos"): com esta fonte, ao tamanho dela, não há frações e o texto sai igual
ao do XP. Noutros tamanhos fica aos quadrados (só serve para esse tamanho).

O TrueType é escrito à mão (sem dependências): só contornos retangulares.

    pixelfont.py <tahoma.ttf> <px> <família> <Regular|Bold> <saída.ttf>
    pixelfont.py mix <normal.ttf> <negrito.ttf> <px> <px grande> <família> <saída.ttf>

"mix" junta numa só fonte o normal, o negrito (em U+E000 + código) e o normal
num tamanho maior (U+E400 + código), mais um espaço de 1 px (U+F8F0): para
escrever texto com negritos e títulos num só bloco (a página de erro do IE,
tools/builders/ieerror.py), e um .json com as larguras de cada um.
"""
import math
import os
import struct
import subprocess
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import ttf  # noqa: E402

U = 64                                  # unidades por píxel
CHARS = [c for r in ((0x20, 0x7F), (0xA0, 0x180), (0x2010, 0x2027)) for c in range(*r)] \
    + [0x20AC, 0x2122, 0x2190, 0x2191, 0x2192, 0x2193, 0x25CF]


def _gid_lsb(t):
    """(código -> glifo, glifo -> lsb em unidades) da cmap 3/1 e da hmtx"""
    cm = t["cmap"]
    n, = struct.unpack_from(">H", cm, 2)
    sub = next(off for p, e, off in (struct.unpack_from(">HHI", cm, 4 + 8 * i) for i in range(n))
               if (p, e) == (3, 1))
    segx2, = struct.unpack_from(">H", cm, sub + 6)
    seg = segx2 // 2
    ends = struct.unpack_from(f">{seg}H", cm, sub + 14)
    starts = struct.unpack_from(f">{seg}H", cm, sub + 16 + segx2)
    deltas = struct.unpack_from(f">{seg}h", cm, sub + 16 + 2 * segx2)
    rp = sub + 16 + 3 * segx2
    roffs = struct.unpack_from(f">{seg}H", cm, rp)
    nh, = struct.unpack_from(">H", t["hhea"], 34)

    def gid(c):
        for i in range(seg):
            if starts[i] <= c <= ends[i]:
                if roffs[i] == 0:
                    return (c + deltas[i]) & 0xFFFF
                g, = struct.unpack_from(">H", cm, rp + 2 * i + roffs[i] + 2 * (c - starts[i]))
                return (g + deltas[i]) & 0xFFFF if g else 0
        return 0

    def lsb(g):
        if g < nh:
            return struct.unpack_from(">Hh", t["hmtx"], 4 * g)[1]
        return struct.unpack_from(">h", t["hmtx"], 4 * nh + 2 * (g - nh))[0]
    return gid, lsb


def glyphs(path, px):
    """{código: (avanço em px, [(x0, y0, x1, y1) em px, y para cima])}"""
    from PIL import ImageFont
    font = ImageFont.truetype(path, px, layout_engine=ImageFont.Layout.BASIC)
    t = ttf.tables(path)
    upem, = struct.unpack_from(">H", t["head"], 18)
    gid, lsb = _gid_lsb(t)
    out = {}
    for c in CHARS:
        ch = chr(c)
        try:
            mask, (ox, oy) = font.getmask2(ch, mode="1", anchor="ls")
        except Exception:
            continue
        w, h = mask.size
        if not w and not ch.isspace():
            continue
        rects = []
        for j in range(h):
            i = 0
            while i < w:
                if mask.getpixel((i, j)):
                    k = i
                    while k < w and mask.getpixel((k, j)):
                        k += 1
                    y = oy + j                      # linha (para baixo, 0 = base)
                    rects.append((ox + i, -(y + 1), ox + k, -y))
                    i = k
                else:
                    i += 1
        # Letras que começam quase na origem (A, v, W, y...): o contorno
        # ajustado cai a meio de uma coluna e o FreeType pinta-a, o GDI não —
        # ficavam 1 px à esquerda do XP. Começam onde o lsb arredondado diz.
        if rects:
            want = math.floor(lsb(gid(c)) * px / upem + 0.5)
            have = min(r[0] for r in rects)
            if have < 0 <= want:
                rects = [(x0 - have, y0, x1 - have, y1) for x0, y0, x1, y1 in rects]
        out[c] = (round(font.getlength(ch)), rects)
    return out


def _checksum(b):
    b += b"\0" * (-len(b) % 4)
    return sum(struct.unpack(f">{len(b) // 4}I", b)) & 0xFFFFFFFF


def _name(family, style):
    recs = [(1, family), (2, style), (3, f"{family} {style}; zorin-xp"),
            (4, f"{family} {style}" if style != "Regular" else family), (5, "Version 1.0"),
            (6, (family + "-" + style).replace(" ", ""))]
    strings = b""
    rows = b""
    for nid, s in recs:
        enc = s.encode("utf-16-be")
        rows += struct.pack(">6H", 3, 1, 0x409, nid, len(enc), len(strings))
        strings += enc
    return struct.pack(">3H", 0, len(recs), 6 + 12 * len(recs)) + rows + strings


def _cmap(codes):
    """formato 4: códigos (ordenados) -> glifo i+1 (o 0 é .notdef)"""
    segs = []
    for gid, c in enumerate(codes, 1):
        if segs and c == segs[-1][1] + 1 and gid - c == segs[-1][2]:
            segs[-1][1] = c
        else:
            segs.append([c, c, gid - c])
    segs.append([0xFFFF, 0xFFFF, 1])
    n = len(segs)
    sr = 2 * (1 << (n.bit_length() - 1))
    body = struct.pack(">4H", 2 * n, sr, (sr // 2).bit_length() - 1, 2 * n - sr)
    body += b"".join(struct.pack(">H", s[1]) for s in segs) + b"\0\0"
    body += b"".join(struct.pack(">H", s[0]) for s in segs)
    body += b"".join(struct.pack(">h", ((s[2] + 0x8000) & 0xFFFF) - 0x8000) for s in segs)
    body += b"\0\0" * n
    sub = struct.pack(">3H", 4, 6 + len(body), 0) + body
    return struct.pack(">2H", 0, 1) + struct.pack(">2HI", 3, 1, 12) + sub


BOLD, BIG, SPACER = 0xE000, 0xE400, 0xF8F0


def mix(regular, bold, px, big_px, family, out):
    """Normal + negrito (BOLD + código) + grande (BIG + código) + espaçador."""
    import json
    g = glyphs(regular, px)
    gb = glyphs(bold, px)
    gh = glyphs(regular, big_px)
    merged = dict(g)
    for c, v in gb.items():
        if c < 0x400:
            merged[BOLD + c] = v
    for c, v in gh.items():
        if c < 0x400:
            merged[BIG + c] = v
    merged[SPACER] = (1, [])
    build(regular, px, family, "Regular", out, merged)
    widths = {"n": {c: v[0] for c, v in g.items()}, "b": {c: v[0] for c, v in gb.items()},
              "h": {c: v[0] for c, v in gh.items()}}
    with open(os.path.splitext(out)[0] + ".json", "w") as f:
        json.dump(widths, f)


def build(path, px, family, style, out, g=None):
    t = ttf.tables(path)
    upem, = struct.unpack_from(">H", t["head"], 18)
    asc, desc = ttf.gdi_ascent_descent(t, px)
    ul_pos, ul_thick = struct.unpack_from(">hh", t["post"], 8)
    if g is None:
        g = glyphs(path, px)
    codes = sorted(g)
    bold = style == "Bold"

    glyf = b""
    loca = [0]
    hmtx = b""
    maxpts = maxcont = 0
    bbox = [0, 0, 0, 0]
    space = g.get(0x20, (px // 3, []))[0]
    entries = [(space, [])] + [g[c] for c in codes]       # .notdef = vazio
    for adv, rects in entries:
        if rects:
            xs = [r[0] for r in rects] + [r[2] for r in rects]
            ys = [r[1] for r in rects] + [r[3] for r in rects]
            gb = (min(xs) * U, min(ys) * U, max(xs) * U, max(ys) * U)
            bbox = [min(bbox[0], gb[0]), min(bbox[1], gb[1]), max(bbox[2], gb[2]), max(bbox[3], gb[3])]
            ends, pts = [], []
            for x0, y0, x1, y1 in rects:            # sentido dos ponteiros do relógio
                pts += [(x0 * U, y0 * U), (x0 * U, y1 * U), (x1 * U, y1 * U), (x1 * U, y0 * U)]
                ends.append(len(pts) - 1)
            data = struct.pack(">h4h", len(rects), *gb)
            data += struct.pack(f">{len(ends)}H", *ends) + struct.pack(">H", 0)
            data += b"\x01" * len(pts)
            px_, py_ = 0, 0
            xd = yd = b""
            for x, y in pts:
                xd += struct.pack(">h", x - px_)
                yd += struct.pack(">h", y - py_)
                px_, py_ = x, y
            data += xd + yd
            data += b"\0" * (-len(data) % 4)
            glyf += data
            maxpts = max(maxpts, len(pts))
            maxcont = max(maxcont, len(rects))
            lsb = gb[0]
        else:
            lsb = 0
        loca.append(len(glyf))
        hmtx += struct.pack(">Hh", adv * U, lsb)

    n = len(entries)
    em = px * U
    head = struct.pack(">IIIIHHqqhhhhHHhhh", 0x00010000, 0x00010000, 0, 0x5F0F3CF5,
                       0x000B, em, 0, 0, *bbox, 1 if bold else 0, 8, 2, 1, 0)
    advmax = max(e[0] for e in entries) * U
    hhea = struct.pack(">I3hH3h3h4hhH", 0x00010000, asc * U, -desc * U, 0, advmax,
                       bbox[0], 0, bbox[2], 1, 0, 0, 0, 0, 0, 0, 0, n)
    maxp = struct.pack(">IH13H", 0x00010000, n, maxpts, maxcont, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0)
    avg = round(sum(e[0] for e in entries) / n) * U
    os2 = struct.pack(">hHHHhhhhhhhhhhhh10s4I4sHHHhhhHHII hhHHH",
                      4, avg, 700 if bold else 400, 5, 0,
                      em // 2, em // 2, 0, em // 8, em // 2, em // 2, 0, em // 3,
                      U, em // 2, 0, b"\x02\x0b\x06\x04\x03\x05\x04\x04\x02\x04",
                      0x00000003, 0, 0, 0, b"ZXP ",
                      (0x20 if bold else 0x40) | 0x80, codes[0], min(codes[-1], 0xFFFF),
                      asc * U, -desc * U, 0, asc * U, desc * U, 1, 0,
                      round(px * 0.5) * U, round(px * 0.7) * U, 0, 0x20, 1)
    post = struct.pack(">IIhhIIIII", 0x00030000, 0, -round(ul_pos * px / upem) * U * -1,
                       max(1, round(ul_thick * px / upem)) * U, 0, 0, 0, 0, 0)
    tables = {
        "OS/2": os2, "cmap": _cmap(codes), "glyf": glyf, "head": head, "hhea": hhea,
        "hmtx": hmtx, "loca": struct.pack(f">{len(loca)}I", *loca), "maxp": maxp,
        "name": _name(family, style), "post": post,
    }
    tags = sorted(tables)
    nt = len(tags)
    sr = 16 * (1 << (nt.bit_length() - 1))
    hdr = struct.pack(">IHHHH", 0x00010000, nt, sr, (sr // 16).bit_length() - 1, nt * 16 - sr)
    off = 12 + 16 * nt
    dirs = b""
    blob = b""
    for tag in tags:
        d = tables[tag]
        dirs += struct.pack(">4sIII", tag.encode(), _checksum(d), off + len(blob), len(d))
        blob += d + b"\0" * (-len(d) % 4)
    font = bytearray(hdr + dirs + blob)
    adj = (0xB1B0AFBA - _checksum(bytes(font))) & 0xFFFFFFFF
    hoff = 12 + 16 * nt + sum(len(tables[x]) + (-len(tables[x]) % 4) for x in tags[:tags.index("head")])
    struct.pack_into(">I", font, hoff + 8, adj)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "wb").write(font)


def export(path, px, family, style, out):
    """Num processo à parte com o FreeType v35 (o GDI do XP)."""
    env = dict(os.environ, FREETYPE_PROPERTIES="truetype:interpreter-version=35")
    subprocess.run([sys.executable, os.path.abspath(__file__), path, str(px), family, style, out],
                   check=True, env=env)


def export_mix(regular, bold, px, big_px, family, out):
    env = dict(os.environ, FREETYPE_PROPERTIES="truetype:interpreter-version=35")
    subprocess.run([sys.executable, os.path.abspath(__file__), "mix", regular, bold, str(px),
                    str(big_px), family, out], check=True, env=env)


if __name__ == "__main__":
    if sys.argv[1] == "mix":
        mix(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6], sys.argv[7])
    else:
        build(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
