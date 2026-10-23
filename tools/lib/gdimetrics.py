"""Glyph widths as XP's GDI uses them (for gdiText.js).

XP advances each glyph by the whole width TrueType hinting gives it (v35
interpreter, the hdmx table), without kerning. GNOME's Pango uses the
unhinted widths and rounds the positions — the text gets different spacing
(measured on the welcome screen's "Desligar computador": 165 px against
XP's 173 px, which match these widths glyph for glyph).

Writes gdi-metrics.json: per font file and size in px, the ascent, the
descent, the underline and the width of each character (Latin). Runs in a
separate process (FreeType reads FREETYPE_PROPERTIES when it starts):
    python3 gdimetrics.py <XP Fonts folder> <out.json>
"""
import json
import os
import struct
import subprocess
import sys

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import ttf  # noqa: E402

FILES = ["tahoma.ttf", "tahomabd.ttf", "arial.ttf", "arialbd.ttf", "arialbi.ttf",
         "framd.ttf", "framdit.ttf", "trebuc.ttf", "trebucbd.ttf"]
SIZES = [11, 12, 13, 19, 21, 48]
CHARS = [c for r in ((0x20, 0x7F), (0xA0, 0x180), (0x2010, 0x2027)) for c in range(*r)] + [0x25CF]


def main(fonts, out):
    from PIL import ImageFont
    res = {}
    for name in FILES:
        path = next((os.path.join(fonts, f) for f in os.listdir(fonts) if f.lower() == name), None)
        if not path:
            continue
        t = ttf.tables(path)
        upem, = struct.unpack_from(">H", t["head"], 18)
        ul_pos, ul_thick = struct.unpack_from(">hh", t["post"], 8)
        for px in SIZES:
            font = ImageFont.truetype(path, px, layout_engine=ImageFont.Layout.BASIC)
            asc, desc = ttf.gdi_ascent_descent(t, px)
            adv = {}
            for c in CHARS:
                ch = chr(c)
                if font.getmask2(ch)[0].size[0] or ch.isspace():
                    adv[str(c)] = round(font.getlength(ch))
            res[f"{name[:-4]}|{px}"] = {
                "a": asc, "d": desc,
                "ul": round(-ul_pos * px / upem), "ut": max(1, round(ul_thick * px / upem)),
                "adv": adv,
            }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, separators=(",", ":"))


def export(fonts, out):
    env = dict(os.environ, FREETYPE_PROPERTIES="truetype:interpreter-version=35")
    subprocess.run([sys.executable, os.path.abspath(__file__), fonts, out], check=True, env=env)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
