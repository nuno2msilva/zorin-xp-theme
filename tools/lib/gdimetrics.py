"""Larguras das letras como o GDI do XP as usa (para gdiText.js).

O XP avança cada letra a largura inteira que o hinting TrueType lhe dá
(interpretador v35, a tabela hdmx), sem kerning. O Pango do GNOME usa as
larguras sem hinting e arredonda as posições — o texto fica com espaços
diferentes (medido no "Desligar computador" do ecrã de boas-vindas: 165 px
contra os 173 px do XP, que coincidem letra a letra com estas larguras).

Gera gdi-metrics.json: por ficheiro de letra e tamanho em px, a subida, a
descida, o sublinhado e a largura de cada carácter (Latim). Corre num
processo à parte (o FreeType lê FREETYPE_PROPERTIES ao arrancar):
    python3 gdimetrics.py <pasta Fonts do XP> <saída.json>
"""
import json
import os
import struct
import subprocess
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
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
