#!/usr/bin/env python3
"""Builds the Zorin XP theme from assets/ (the resources extracted from XP
by tools/extract.py) and src/ (the theme's code and stylesheets).

Usage: build.py [--out build] [components...]
Components: sounds cursors fonts gtk shell extension icons filechooser zen
logon boot (default: sounds cursors fonts gtk shell extension icons)
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from builders import cursors  # noqa: E402
from builders import filechooser  # noqa: E402
from builders import zenie  # noqa: E402
from builders import gtktheme  # noqa: E402
from builders import icons  # noqa: E402
from builders import logon  # noqa: E402
from builders import bootscreen  # noqa: E402
from builders import shelltheme  # noqa: E402
from builders import sounds  # noqa: E402
from lib import assets  # noqa: E402
from lib.paths import ROOT


def _fc_faces(path):
    """(family, weight, slant) of each font in the file (a .ttc has several)."""
    r = subprocess.run(["fc-scan", "--format", "%{family[0]}|%{weight}|%{slant}\n", path],
                       capture_output=True, text=True)
    return {tuple(l.split("|")) for l in r.stdout.splitlines() if l}


def build_fonts(out):
    """All the XP TrueType fonts (the UI ones with GDI's widths,
    fontfix.py) and the UI bitmap fonts; plus the fontconfig rule that
    prefers the XP ones over system copies with the same name."""
    dst = os.path.join(out, "WindowsXP")
    os.makedirs(dst, exist_ok=True)
    from lib import fontfix
    src_dir = assets.fonts_dir()
    families = set()
    for f in sorted(os.listdir(src_dir)):
        low = f.lower()
        src = os.path.join(src_dir, f)
        if low.endswith((".ttf", ".ttc")):
            family = fontfix.family_of(low)
            if family:
                # character widths as in XP's GDI (see fontfix.py)
                fontfix.fix(src, os.path.join(dst, low), family)
                # (and the original, for the applications with a browser engine:
                # the widths are fixed for the UI's size, and at the sizes of a
                # page some letters came out too wide or too tight —
                # src/fontconfig/zorin-xp-browser-fonts)
                os.makedirs(os.path.join(out, "browser"), exist_ok=True)
                shutil.copyfile(src, os.path.join(out, "browser", low))
            else:
                shutil.copyfile(src, os.path.join(dst, low))
            families |= _fc_faces(src)
        elif low.endswith(".fon"):      # (only the UI ones: see catalog.py)
            shutil.copyfile(src, os.path.join(dst, low))
    for conf in ("60-windows-xp.conf", "61-windows-xp-arial.conf"):
        shutil.copyfile(os.path.join(ROOT, "src", "fontconfig", conf), os.path.join(out, conf))

    # copies of the same families in other folders (e.g. msttcorefonts): rejected,
    # so that the XP version wins; and the XP bitmap fonts accepted (Ubuntu
    # rejects bitmap fonts by default)
    home_fonts = os.path.join(os.path.expanduser("~"), ".local", "share", "fonts", "WindowsXP")
    # (only the ones XP replaces: same family, same weight and slant)
    listing = subprocess.run(["fc-list", "--format", "%{family[0]}|%{weight}|%{slant}|%{file}\n"],
                             capture_output=True, text=True).stdout.splitlines()
    clashes = sorted({parts[3] for parts in (l.split("|", 3) for l in listing)
                      if len(parts) == 4 and tuple(parts[:3]) in families
                      and not parts[3].startswith(home_fonts)})
    from xml.sax.saxutils import escape
    with open(os.path.join(out, "62-windows-xp-prefer.conf"), "w") as f:
        f.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                "<!-- Zorin XP: as letras do XP valem sobre cópias com o mesmo nome noutras pastas"
                " (gerado pelo build para esta máquina) -->\n<fontconfig>\n  <selectfont>\n")
        f.write(f"    <acceptfont><glob>{escape(home_fonts)}/*.fon</glob></acceptfont>\n")
        if clashes:
            f.write("    <rejectfont>\n")
            for c in clashes:
                f.write(f"      <glob>{escape(c)}</glob>\n")
            f.write("    </rejectfont>\n")
        f.write("  </selectfont>\n</fontconfig>\n")
    return dst


def build_extension(out):
    """GNOME Shell extension + the frame assets it uses."""
    from lib import msstyles
    from builders import gtkassets
    src = os.path.join(ROOT, "src", "shell-extension")
    for uuid in os.listdir(src):
        dst = os.path.join(out, uuid)
        shutil.copytree(os.path.join(src, uuid), dst)
        if uuid.startswith("zorin-xp@"):
            # welcome screen, exit screens and the turn off / log off dialogs
            # (logonui, winlogon, msgina, shell32)
            from builders import logon
            logon.export_session(os.path.join(dst, "logon"))
            # font widths as XP's GDI uses them (gdiText.js)
            from lib import gdimetrics
            gdimetrics.export(assets.fonts_dir(), os.path.join(dst, "gdi-metrics.json"))
            tmp = os.path.join(out, ".assets")
            ms = assets.theme("luna")
            gtkassets.export(ms, tmp)
            os.makedirs(os.path.join(dst, "assets"))
            for f in os.listdir(tmp):
                if f.startswith(("caption-left-", "caption-right-", "frame-left-strip-",
                                 "frame-right-strip-", "frame-bottom-strip-")) and "@2" not in f:
                    shutil.copyfile(os.path.join(tmp, f), os.path.join(dst, "assets", f))
            shutil.rmtree(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build"))
    ap.add_argument("--no-cursor-shadow", action="store_true")
    ap.add_argument("components", nargs="*")
    a = ap.parse_args()
    comps = a.components or ["sounds", "cursors", "fonts", "gtk", "shell", "extension", "icons"]
    for c in comps:
        if c in ("folders", "explorer"):
            continue        # (nothing to generate: install.sh handles the folders, translations and Files)
        out = os.path.join(a.out, c)
        if os.path.exists(out):
            shutil.rmtree(out)
        os.makedirs(out)
        if c == "sounds":
            sounds.build(out)
        elif c == "cursors":
            cursors.build(out, shadow=not a.no_cursor_shadow)
        elif c == "fonts":
            build_fonts(out)
        elif c == "gtk":
            gtktheme.build(out)
        elif c == "extension":
            build_extension(out)
        elif c == "icons":
            icons.build(out)
        elif c == "shell":
            shelltheme.build(out)
        elif c == "boot":
            bootscreen.build(out)
        elif c == "filechooser":
            filechooser.build(out)
        elif c == "zen":
            # uses the Luna pieces already made for the GTK theme
            gtk_assets = os.path.join(os.path.dirname(out), "gtk", "WindowsXP-Luna", "gtk-assets")
            if not os.path.isdir(gtk_assets):
                gtktheme.build(os.path.join(os.path.dirname(out), "gtk"))
            zenie.build(gtk_assets, out)
        elif c == "logon":
            shutil.rmtree(out)
            logon.build(out)
        else:
            sys.exit(f"componente desconhecido: {c}")
        print(f"  ✓ {c} -> {out}")


if __name__ == "__main__":
    main()
