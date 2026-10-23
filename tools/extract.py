#!/usr/bin/env python3
"""Extracts from a copy of the XP Windows folder the resources the theme uses,
into assets/ (see tools/catalog.py, with the name and source of each one).

Usage:  tools/extract.py [--windows windows/xp-pro-pt] [--locale pt-PT] [groups...]
Groups: themes locale icons images sounds fonts cursors (default: all)

It is the only step that reads Windows; the build (tools/build.py) only
reads assets/. Each assets/ folder gets an ORIGEM.md with the source of
each file.
"""
import argparse
import fnmatch
import json
import ntpath
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import catalog
from lib import dlgtemplate
from lib import msstyles
from lib import wincursor
from lib import winicons
from lib import winmenus
from lib.paths import ASSETS, DEFAULT_LOCALE, DEFAULT_WINDOWS, find_ci
from lib.regf import Hive


class Windows:
    """A copy of the Windows folder: files and DLL/EXE resources."""

    def __init__(self, root):
        self.root = root
        self._pes = {}

    def path(self, rel):
        """Path of a file: "x.dll" in system32 (or dllcache, or in the
        root); "folder/file" relative to the root."""
        parts = rel.replace("\\", "/").split("/")
        if len(parts) > 1:
            return find_ci(self.root, *parts)
        for where in (("system32",), ("system32", "dllcache"), ()):
            try:
                return find_ci(self.root, *where, rel)
            except FileNotFoundError:
                pass
        raise FileNotFoundError(f"{rel} (em {self.root})")

    def pe(self, rel):
        if rel not in self._pes:
            self._pes[rel] = msstyles.PEResources(self.path(rel))
        return self._pes[rel]


def write_origin(folder, title, rows):
    """ORIGEM.md: where each file in the folder came from."""
    with open(os.path.join(folder, "ORIGEM.md"), "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\nGerado por `tools/extract.py` (ver `tools/catalog.py`).\n\n")
        f.write("| Ficheiro | Origem no Windows |\n|---|---|\n")
        for name, origin in rows:
            f.write(f"| `{name}` | {origin} |\n")


def fresh(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    return folder


# --------------------------------------------------------------------------
# Temas
# --------------------------------------------------------------------------
def extract_themes(win, out):
    for name, spec in catalog.THEMES.items():
        dst = fresh(os.path.join(out, "themes", name))
        ms = msstyles.MsStyles(win.path(spec["msstyles"]), spec["ini"])
        rows = []
        with open(os.path.join(dst, "theme.ini"), "w", encoding="utf-8") as f:
            f.write(ms.ini_text.replace("\r\n", "\n"))
        rows.append(("theme.ini", f"{spec['msstyles']}, texto {spec['ini']}"))
        # every image the INI uses, with the INI's name (without the folder)
        bitmaps = fresh(os.path.join(dst, "bitmaps"))
        seen = {}
        for part in ms.parts.values():
            for value in part.props.values():
                if not value.lower().endswith(".bmp"):
                    continue
                base = ntpath.basename(value)[:-4]
                if base.lower() in seen:
                    continue
                seen[base.lower()] = value
                ms.bitmap(value).save(os.path.join(bitmaps, f"{base}.png"))
                rows.append((f"bitmaps/{base}.png", f"{spec['msstyles']}, {value}"))
        # the Explorer task pane
        shell = fresh(os.path.join(dst, "shell"))
        style = win.pe(spec["shellstyle"])
        for key, rid in catalog.SHELLSTYLE.items():
            msstyles.dib_to_image(style.get(2, rid)).save(os.path.join(shell, f"{key}.png"))
            rows.append((f"shell/{key}.png", f"{spec['shellstyle']}, bitmap {rid}"))
        shutil.copyfile(win.path(spec["theme_file"]), os.path.join(dst, os.path.basename(spec["theme_file"])))
        rows.append((os.path.basename(spec["theme_file"]), spec["theme_file"]))
        write_origin(dst, f"Tema {spec['title']}", sorted(rows))
        print(f"  ✓ themes/{name}: {len(seen)} imagens do tema, {len(catalog.SHELLSTYLE)} do Explorador")


# --------------------------------------------------------------------------
# Sounds and fonts: copies, with the Windows name
# --------------------------------------------------------------------------
def extract_sounds(win, out):
    dst = fresh(os.path.join(out, "sounds"))
    src = win.path(catalog.SOUNDS_DIR)
    rows = []
    for f in sorted(os.listdir(src)):
        if fnmatch.fnmatch(f.lower(), catalog.SOUNDS_GLOB):
            shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
            rows.append((f, f"{catalog.SOUNDS_DIR}/{f}"))
    write_origin(dst, "Sons", rows)
    print(f"  ✓ sounds: {len(rows)}")


def _fc_family(path):
    """Family of the (first) font in the file (a .fon has several)."""
    out = subprocess.run(["fc-scan", "--format", "%{family[0]}\n", path], capture_output=True, text=True)
    return (out.stdout.splitlines() or [""])[0]


def extract_fonts(win, out):
    dst = fresh(os.path.join(out, "fonts"))
    src = win.path(catalog.FONTS_DIR)
    rows = []
    for f in sorted(os.listdir(src)):
        low = f.lower()
        path = os.path.join(src, f)
        if low.endswith((".ttf", ".ttc")) or (
                low.endswith(".fon") and _fc_family(path) in catalog.FONT_BITMAP_FAMILIES):
            shutil.copyfile(path, os.path.join(dst, f))
            rows.append((f, f"{catalog.FONTS_DIR}/{f}"))
    write_origin(dst, "Letras", rows)
    print(f"  ✓ fonts: {len(rows)}")


# --------------------------------------------------------------------------
# Cursors: each one's RT_GROUP_CURSOR group, in a .cur file
# --------------------------------------------------------------------------
def cur_file(pe, gid):
    """RT_GROUP_CURSOR + RT_CURSOR -> bytes of a .cur file (every size,
    with the hotspot)."""
    group = pe.get(wincursor.RT_GROUP_CURSOR, gid)
    _r, _t, count = struct.unpack_from("<HHH", group, 0)
    images = []
    for i in range(count):
        _w, _h2, _planes, _bpp, _size, cid = struct.unpack_from("<HHHHIH", group, 6 + i * 14)
        data = pe.get(wincursor.RT_CURSOR, cid)
        hx, hy = struct.unpack_from("<HH", data, 0)
        dib = data[4:]
        _hs, w, h2, _p, bpp = struct.unpack_from("<IiiHH", dib, 0)
        images.append((w, abs(h2) // 2, bpp, hx, hy, dib))
    head = struct.pack("<HHH", 0, 2, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for w, h, bpp, hx, hy, dib in images:
        colors = (1 << bpp) if bpp < 8 else 0
        entries += struct.pack("<BBBBHHII", w & 0xFF, h & 0xFF, colors & 0xFF, 0, hx, hy, len(dib), offset)
        blobs += dib
        offset += len(dib)
    return head + entries + blobs


def extract_cursors(win, out):
    dst = fresh(os.path.join(out, "cursors"))
    rows = []
    for name, (dll, gid) in catalog.CURSORS.items():
        with open(os.path.join(dst, f"{name}.cur"), "wb") as f:
            f.write(cur_file(win.pe(dll), gid))
        rows.append((f"{name}.cur", f"{dll}, cursor {gid}"))
    write_origin(dst, "Cursores (esquema \"Predefinição do Windows\")", rows)
    print(f"  ✓ cursors: {len(rows)}")


# --------------------------------------------------------------------------
# Icons: each icon group in an .ico (every size and depth)
# --------------------------------------------------------------------------
def extract_icons(win, out):
    dst = fresh(os.path.join(out, "icons"))
    rows, seen = [], {}
    for name, (dll, gid) in catalog.ICONS.items():
        pe = win.pe(dll)
        if gid is None:
            gid = winicons.group_ids(pe)[0]      # the program's icon
        key = (dll.lower(), gid)
        if key in seen:
            raise SystemExit(f"catalog.ICONS: {name} e {seen[key]} são o mesmo ícone ({dll} {gid})")
        seen[key] = name
        data = winicons.ico_file(pe, gid)
        if len(data) <= 6:
            raise SystemExit(f"catalog.ICONS: {name}: {dll} não tem o ícone {gid}")
        with open(os.path.join(dst, f"{name}.ico"), "wb") as f:
            f.write(data)
        rows.append((f"{name}.ico", f"{dll}, ícone {gid}"))
    write_origin(dst, "Ícones", rows)
    print(f"  ✓ icons: {len(rows)}")


# --------------------------------------------------------------------------
# DLL images: PNG (the 32-bit ones with their alpha) and, for the boot
# screen, the bitmaps as they are (.bmp)
# --------------------------------------------------------------------------
def extract_images(win, out):
    dst = fresh(os.path.join(out, "images"))
    rows = []
    for name, (dll, rid) in catalog.IMAGES.items():
        path = os.path.join(dst, f"{name}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        msstyles.dib_to_image(win.pe(dll).get(2, rid)).save(path)
        rows.append((f"{name}.png", f"{dll}, bitmap {rid}"))
    for path, (dll, res) in catalog.NAMED_IMAGES.items():
        full = os.path.join(dst, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(_named(win.pe(dll), res))
        rows.append((path, f"{dll}, {res}"))
    for name, (dll, rid) in catalog.RAW_BITMAPS.items():
        path = os.path.join(dst, f"{name}.bmp")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dib = win.pe(dll).get(2, rid)
        with open(path, "wb") as f:
            f.write(msstyles.bmp_file(dib) + dib)
        rows.append((f"{name}.bmp", f"{dll}, bitmap {rid} (tal e qual)"))
    write_origin(dst, "Imagens", rows)
    print(f"  ✓ images: {len(rows)}")


# --------------------------------------------------------------------------
# Texts of a language: string tables, dialogs and menus of each file
# --------------------------------------------------------------------------
def string_tables(pe):
    """{id: text} from every string table (RT_STRING, 16 per block)."""
    out = {}
    for rtype, block_id in sorted(k for k in pe.resources if k[0] == 6):
        data = pe.get(rtype, block_id)
        o = 0
        for i in range(16):
            if o + 2 > len(data):
                break
            n, = struct.unpack_from("<H", data, o)
            o += 2
            if n:
                text = data[o:o + n * 2].decode("utf-16le").replace("\r\n", "\n")
                out[(block_id - 1) * 16 + i] = text
            o += n * 2
    return out


def extract_locale(win, out, locale):
    dst = fresh(os.path.join(out, "locales", locale))
    rows = []
    for name in catalog.TEXT_FILES:
        pe = win.pe(name)
        dialogs = {}
        for rtype, rid in sorted(k for k in pe.resources if k[0] == 5 and isinstance(k[1], int)):
            try:
                dialogs[rid] = dlgtemplate.dialog(pe, rid)
            except ValueError:                  # (DIALOGEX only)
                pass
        menus = {rid: winmenus.parse(pe.get(4, rid))
                 for _t, rid in sorted(k for k in pe.resources if k[0] == 4 and isinstance(k[1], int))}
        data = {"strings": string_tables(pe), "dialogs": dialogs, "menus": menus}
        base = name.rsplit(".", 1)[0].lower()
        with open(os.path.join(dst, f"{base}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        rows.append((f"{base}.json", f"{name}: {len(data['strings'])} textos, "
                     f"{len(dialogs)} diálogos, {len(menus)} menus"))
    hives = {}
    registry = {}
    for key, (hive, path, value) in catalog.REGISTRY_TEXTS.items():
        if hive not in hives:
            hives[hive] = Hive(win.path(f"system32/config/{hive}"))
        registry[key] = hives[hive].value(path, value)
    with open(os.path.join(dst, "registry.json"), "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=1)
    rows.append(("registry.json", "registo: " + ", ".join(
        f"{h}\\{p}" for h, p, _v in catalog.REGISTRY_TEXTS.values())))
    for path, (dll, res) in catalog.LOCALE_FILES.items():
        full = os.path.join(dst, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(_named(win.pe(dll), res))
        rows.append((path, f"{dll}, {res}"))
    write_origin(dst, f"Textos ({locale})", rows)
    print(f"  ✓ locales/{locale}: {len(rows)} ficheiros")


def _named(pe, name):
    """Named resource (e.g. "DNSERROR.HTM"), of any type."""

    for (_t, n), data in pe.resources.items():
        if isinstance(n, str) and n.upper() == name.upper():
            return data
    raise KeyError(name)


GROUPS = {
    "themes": extract_themes,
    "locale": extract_locale,
    "icons": extract_icons,
    "images": extract_images,
    "sounds": extract_sounds,
    "fonts": extract_fonts,
    "cursors": extract_cursors,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--windows", default=DEFAULT_WINDOWS, help="cópia da pasta Windows")
    ap.add_argument("--locale", default=DEFAULT_LOCALE, help="língua dos textos (assets/locales/...)")
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument("groups", nargs="*", help=f"grupos: {' '.join(GROUPS)} (por omissão: todos)")
    a = ap.parse_args()
    unknown = [g for g in a.groups if g not in GROUPS]
    if unknown:
        ap.error(f"grupo desconhecido: {' '.join(unknown)}")
    win = Windows(a.windows)
    print(f"A extrair de {a.windows} para {a.out}")
    for g in a.groups or GROUPS:
        if g == "locale":
            GROUPS[g](win, a.out, a.locale)
        else:
            GROUPS[g](win, a.out)


if __name__ == "__main__":
    main()
