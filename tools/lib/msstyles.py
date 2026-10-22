#!/usr/bin/env python3
"""Leitura de ficheiros .msstyles do Windows XP (DLLs PE com recursos).

Extrai os bitmaps e o INI do esquema de cores, interpreta o INI (as mesmas
secções/propriedades que o uxtheme.dll usa) e corta as imagens multi-estado
em PNGs individuais com transparência correta.
"""
import io
import re
import struct
from dataclasses import dataclass, field

from PIL import Image

RT_BITMAP = 2


# --------------------------------------------------------------------------
# Recursos PE
# --------------------------------------------------------------------------
class PEResources:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        if d[pe:pe + 4] != b"PE\0\0":
            raise ValueError(f"{path}: não é um ficheiro PE")
        nsec, = struct.unpack_from("<H", d, pe + 6)
        opt_size, = struct.unpack_from("<H", d, pe + 20)
        opt = pe + 24
        magic, = struct.unpack_from("<H", d, opt)
        dd = opt + (96 if magic == 0x10B else 112)
        self.rsrc_rva, _ = struct.unpack_from("<II", d, dd + 2 * 8)
        self.sections = []
        sec = opt + opt_size
        for i in range(nsec):
            vsize, va, rsize, rptr = struct.unpack_from("<IIII", d, sec + i * 40 + 8)
            self.sections.append((va, max(vsize, rsize), rptr))
        self.rsrc_off = self._rva2off(self.rsrc_rva)
        self.resources = {}  # (type, name) -> bytes
        self._walk()

    def _rva2off(self, rva):
        for va, size, ptr in self.sections:
            if va <= rva < va + size:
                return rva - va + ptr
        raise ValueError(f"RVA {rva:#x} fora das secções")

    def _name(self, entry_name):
        if entry_name & 0x80000000:
            off = self.rsrc_off + (entry_name & 0x7FFFFFFF)
            n, = struct.unpack_from("<H", self.data, off)
            return self.data[off + 2:off + 2 + n * 2].decode("utf-16le")
        return entry_name

    def _entries(self, off):
        named, ids = struct.unpack_from("<HH", self.data, off + 12)
        for i in range(named + ids):
            name, target = struct.unpack_from("<II", self.data, off + 16 + i * 8)
            yield self._name(name), target

    def _walk(self):
        base = self.rsrc_off
        for rtype, t1 in self._entries(base):
            for rname, t2 in self._entries(base + (t1 & 0x7FFFFFFF)):
                for _lang, t3 in self._entries(base + (t2 & 0x7FFFFFFF)):
                    rva, size = struct.unpack_from("<II", self.data, base + t3)
                    off = self._rva2off(rva)
                    self.resources[(rtype, rname)] = self.data[off:off + size]
                    break

    def get(self, rtype, rname):
        return self.resources.get((rtype, rname))


# --------------------------------------------------------------------------
# Bitmaps (DIB sem cabeçalho de ficheiro)
# --------------------------------------------------------------------------
def bmp_file(dib):
    """Cabeçalho de ficheiro .bmp (BITMAPFILEHEADER) para um DIB de recurso."""
    hsize, _w, _h, _planes, bpp, comp = struct.unpack_from("<IiiHHI", dib, 0)
    colors = struct.unpack_from("<I", dib, 32)[0] if hsize >= 36 else 0
    if bpp <= 8 and colors == 0:
        colors = 1 << bpp
    masks = 12 if comp == 3 and hsize == 40 else 0
    return struct.pack("<2sIHHI", b"BM", 14 + len(dib), 0, 0, 14 + hsize + masks + colors * 4)


def dib_to_image(dib):
    """Converte um DIB de recurso em imagem RGBA.

    Bitmaps de 32 bpp do Luna têm alfa por píxel (não pré-multiplicado);
    os restantes são opacos e a transparência é feita por cor-chave.
    """
    hsize, w, h, planes, bpp, comp = struct.unpack_from("<IiiHHI", dib, 0)
    if bpp == 32 and comp in (0, 3):
        off = hsize + (12 if comp == 3 else 0)
        flipped = h > 0
        h = abs(h)
        img = Image.frombuffer("RGBA", (w, h), dib[off:off + w * h * 4], "raw", "BGRA", 0, -1 if flipped else 1)
        return img.copy()
    return Image.open(io.BytesIO(bmp_file(dib) + dib)).convert("RGBA")


def key_out(img, color):
    """Torna transparente uma cor-chave (TransparentColor do uxtheme)."""
    img = img.copy()
    px = img.load()
    r0, g0, b0 = color
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if (r, g, b) == (r0, g0, b0):
                px[x, y] = (0, 0, 0, 0)
    return img


def slice_states(img, count, layout="vertical"):
    count = max(1, count)
    if layout.lower().startswith("h"):
        w = img.width // count
        return [img.crop((i * w, 0, (i + 1) * w, img.height)) for i in range(count)]
    h = img.height // count
    return [img.crop((0, i * h, img.width, (i + 1) * h)) for i in range(count)]


# --------------------------------------------------------------------------
# INI do esquema de cores
# --------------------------------------------------------------------------
@dataclass
class Part:
    name: str
    props: dict = field(default_factory=dict)

    def get(self, key, default=None):
        return self.props.get(key.lower(), default)

    def ints(self, key, default=None):
        v = self.get(key)
        if v is None:
            return default
        return [int(x) for x in re.split(r"[\s,]+", v.strip()) if x]

    def color(self, key, default=None):
        v = self.ints(key)
        return tuple(v[:3]) if v else default

    def flag(self, key, default=False):
        v = self.get(key)
        return default if v is None else v.strip().lower() in ("true", "1", "yes")


def parse_ini(text):
    parts = {}
    cur = None
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            name = line.strip("[]").strip()
            cur = parts.setdefault(name.lower(), Part(name))
        elif "=" in line and cur is not None:
            k, v = line.split("=", 1)
            cur.props[k.strip().lower()] = v.strip()
    return parts


class MsStyles:
    def __init__(self, path, color_ini="NORMALBLUE_INI"):
        self.pe = PEResources(path)
        raw = self.pe.get("TEXTFILE", color_ini)
        if raw is None:
            names = [n for t, n in self.pe.resources if t == "TEXTFILE"]
            raise KeyError(f"{color_ini} não existe; disponíveis: {names}")
        self.ini_text = raw.decode("utf-16le").lstrip("﻿")
        self.parts = parse_ini(self.ini_text)

    def part(self, name):
        return self.parts[name.lower()]

    def bitmap(self, ini_path):
        """'Blue\\FrameCaption.bmp' -> Image RGBA (sem transparência aplicada)."""
        rname = re.sub(r"[\\/.]", "_", ini_path).upper()
        dib = self.pe.get(RT_BITMAP, rname)
        if dib is None:
            raise KeyError(f"bitmap {ini_path} ({rname}) não encontrado")
        return dib_to_image(dib)

    def bitmap_bpp(self, ini_path):
        rname = re.sub(r"[\\/.]", "_", ini_path).upper()
        return struct.unpack_from("<H", self.pe.get(RT_BITMAP, rname), 14)[0]

    def image(self, path, transparent=False, key=(255, 0, 255)):
        """Bitmap com a transparência que o uxtheme lhe daria.

        32 bpp com algum alfa < 255 -> alfa por píxel; caso contrário, se a
        parte for Transparent, a cor-chave (magenta por omissão) é removida.
        """
        img = self.bitmap(path)
        has_alpha = img.getextrema()[3][0] < 255
        if not has_alpha and transparent:
            img = key_out(img, key)
        return img

    def states(self, part_name, image_key="ImageFile", count=None, glyph=False):
        """Imagens de cada estado de uma parte, já com transparência aplicada."""
        p = self.part(part_name)
        path = p.get(image_key)
        if glyph:
            img = self.image(path, p.flag("GlyphTransparent"),
                             p.color("GlyphTransparentColor", (255, 0, 255)))
        else:
            img = self.image(path, p.flag("Transparent"),
                             p.color("TransparentColor", (255, 0, 255)))
        if count is None:
            count = int(p.get("ImageCount", "1"))
        return slice_states(img, count, p.get("ImageLayout", "vertical"))
