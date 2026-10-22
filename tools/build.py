#!/usr/bin/env python3
"""Constrói o tema Zorin XP a partir de assets/ (os recursos extraídos do XP
por tools/extract.py) e de src/ (o código e as folhas de estilo do tema).

Uso: build.py [--out build] [componentes...]
Componentes: sounds cursors fonts gtk shell extension icons filechooser zen
logon boot (por omissão: sounds cursors fonts gtk shell extension icons)
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
    """(família, peso, inclinação) de cada letra do ficheiro (um .ttc tem várias)."""
    r = subprocess.run(["fc-scan", "--format", "%{family[0]}|%{weight}|%{slant}\n", path],
                       capture_output=True, text=True)
    return {tuple(l.split("|")) for l in r.stdout.splitlines() if l}


def build_fonts(out):
    """Todas as letras TrueType do XP (as da interface com as larguras do GDI,
    fontfix.py) e as de mapa de bits da interface; mais a regra do fontconfig
    que dá preferência às do XP sobre cópias do sistema com o mesmo nome."""
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
                # larguras dos caracteres como no GDI do XP (ver fontfix.py)
                fontfix.fix(src, os.path.join(dst, low), family)
            else:
                shutil.copyfile(src, os.path.join(dst, low))
            families |= _fc_faces(src)
        elif low.endswith(".fon"):      # (só as da interface: ver catalog.py)
            shutil.copyfile(src, os.path.join(dst, low))
    for conf in ("60-windows-xp.conf", "61-windows-xp-arial.conf"):
        shutil.copyfile(os.path.join(ROOT, "src", "fontconfig", conf), os.path.join(out, conf))

    # cópias das mesmas famílias noutras pastas (ex.: msttcorefonts): rejeitadas,
    # para valer a versão do XP; e as de mapa de bits do XP aceites (o Ubuntu
    # rejeita letras de mapa de bits por omissão)
    home_fonts = os.path.join(os.path.expanduser("~"), ".local", "share", "fonts", "WindowsXP")
    # (só as que o XP substitui: mesma família, mesmo peso e inclinação)
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
    """Extensão do GNOME Shell + os assets de moldura que ela usa."""
    from lib import msstyles
    from builders import gtkassets
    src = os.path.join(ROOT, "src", "shell-extension")
    for uuid in os.listdir(src):
        dst = os.path.join(out, uuid)
        shutil.copytree(os.path.join(src, uuid), dst)
        if uuid.startswith("zorin-xp@"):
            # ecrã de boas-vindas, ecrãs de saída e diálogos de desligar/terminar
            # sessão (logonui, winlogon, msgina, shell32)
            from builders import logon
            logon.export_session(os.path.join(dst, "logon"))
            # larguras das letras como o GDI do XP (gdiText.js)
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
            continue        # (nada a gerar: o install.sh trata das pastas, traduções e do Ficheiros)
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
            # usa as peças do Luna já feitas para o tema GTK
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
