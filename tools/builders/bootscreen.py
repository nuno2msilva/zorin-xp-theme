"""Ecrã de arranque do XP como tema do Plymouth.

Arranque: o ecrã de 640x480 do ntoskrnl.exe (bitmap 1) com a barra de
progresso (bitmap 8, três blocos de 22x9). As paletas destes bitmaps estão a
zero no recurso — o kernel acende-as a partir do preto com a sua própria
tabela, que é a paleta do bitmap 5 deslocada uma entrada (sem o preto
repetido do início, a acabar em branco; no binário logo a seguir à do
bitmap 5). Confirmado contra o arranque de uma VM XP.

Comportamento medido: acende do preto em ~1,75 s; os blocos andam 8 px a
cada 100 ms dentro da caixa (x 259..376, y 354), com um passo vazio no fim
de cada volta. O ecrã de 640x480 é refeito à resolução do ecrã com as peças no
tamanho original: o logótipo e a barra ao centro, o "Copyright" no canto de
baixo à esquerda e "Microsoft" à direita, às mesmas distâncias das margens.

Desligar/reiniciar: o ecrã de estado do XP ("O Windows está a encerrar...",
winlogon.exe) com as peças do logonui.exe, igual ao que a extensão mostra
antes de a sessão terminar, para a passagem ser contínua.
"""
import json
import os
import struct
import subprocess
import sys

from PIL import Image

from builders import logon
from lib import msstyles
from lib import assets
from lib.paths import ROOT

THEME = "windows-xp"
# peças do bitmap 1 (x0, y0, x1, y1): o resto é preto
PIECES = {"center": (209, 123, 455, 366),      # logótipo e a caixa da barra
          "copyright": (22, 447, 222, 461),     # canto de baixo, à esquerda
          "microsoft": (546, 447, 619, 461)}    # canto de baixo, à direita
FADE_FRAMES = 88          # ~1,75 s a 50 imagens/s
STEP_FRAMES = 5           # 100 ms por passo
BAR = {"x0": 243, "x_end": 371, "step": 8, "y": 354, "clip_l": 259, "clip_r": 377}


def _boot_palette():
    """A paleta com que o kernel acende o ecrã: a do bitmap 5, deslocada uma
    entrada e a acabar em branco."""
    ref = assets.raw_bitmap("boot/palette-source")
    h = struct.unpack_from("<I", ref, 0)[0]
    return ref[h + 4:h + 64] + bytes([255, 255, 255, 0])


def _with_palette(name, pal):
    d = bytearray(assets.raw_bitmap(name))
    h = struct.unpack_from("<I", d, 0)[0]
    d[h:h + 64] = pal
    return msstyles.dib_to_image(bytes(d)).convert("RGBA")


def _render_text(text, font_dir, out):
    """Texto Arial 19 px (14 pt no XP) como o GDI: interpretador v35, hinting
    completo, tons de cinzento — o initramfs não tem a Arial."""
    script = r'''
import sys, cairo, gi
gi.require_version("Pango", "1.0"); gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo
text, out = sys.argv[1], sys.argv[2]
probe = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
def layout(cr):
    fo = cairo.FontOptions(); fo.set_hint_style(cairo.HINT_STYLE_FULL)
    fo.set_hint_metrics(cairo.HINT_METRICS_ON); fo.set_antialias(cairo.ANTIALIAS_GRAY)
    l = PangoCairo.create_layout(cr); PangoCairo.context_set_font_options(l.get_context(), fo)
    PangoCairo.context_set_resolution(l.get_context(), 96)
    fd = Pango.FontDescription("Arial"); fd.set_absolute_size(19 * Pango.SCALE)
    l.set_font_description(fd); l.set_text(text, -1); return l
w, h = layout(cairo.Context(probe)).get_pixel_size()
s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h); cr = cairo.Context(s)
cr.set_source_rgb(239 / 255, 247 / 255, 1); PangoCairo.show_layout(cr, layout(cr)); s.write_to_png(out)
'''
    conf = out + ".fonts.conf"
    with open(conf, "w") as f:
        f.write(f'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'
                f'<fontconfig><include ignore_missing="yes">/etc/fonts/fonts.conf</include>'
                f'<dir>{font_dir}</dir></fontconfig>')
    env = dict(os.environ, FONTCONFIG_FILE=conf,
               FREETYPE_PROPERTIES="truetype:interpreter-version=35")
    subprocess.run([sys.executable, "-c", script, text, out], check=True, env=env)
    os.remove(conf)


def build(out):
    theme = os.path.join(out, THEME)
    import shutil
    shutil.rmtree(theme, ignore_errors=True)
    os.makedirs(theme)
    pal = _boot_palette()
    screen = _with_palette("boot/screen", pal)
    blocks = _with_palette("boot/progress", pal)
    # a barra em 18 passos já recortados à caixa (o último vazio)
    clip_w = BAR["clip_r"] - BAR["clip_l"]
    steps = []
    for i in range(18):
        strip = Image.new("RGBA", (clip_w, 9), (0, 0, 0, 255))
        x = BAR["x0"] + i * BAR["step"]
        if x <= BAR["x_end"]:
            strip.paste(blocks, (x - BAR["clip_l"], 0))
        steps.append(strip)
    # (o resto do bitmap tem de ser preto: senão faltaria alguma peça)
    rest = screen.copy()
    for box in PIECES.values():
        rest.paste((0, 0, 0, 255), box)
    assert rest.convert("RGB").getbbox() is None, "peça do ecrã de arranque por recortar"
    for name, box in PIECES.items():
        screen.crop(box).save(os.path.join(theme, f"boot-{name}.png"))
    for i, strip in enumerate(steps):
        strip.save(os.path.join(theme, f"bar-{i}.png"))

    # ecrã de estado ao desligar: peças do logonui.exe e o texto do winlogon.exe
    tmp = os.path.join(out, ".logon")
    logon.export_images(tmp)
    for name in ("glow", "logo", "divider-top", "divider-bottom"):
        Image.open(os.path.join(tmp, f"{name}.png")).save(os.path.join(theme, f"{name}.png"))
    strings = logon.export_strings()
    fonts = os.path.join(out, ".fonts")
    os.makedirs(fonts, exist_ok=True)
    import shutil
    shutil.copyfile(assets.font("arial.ttf"), os.path.join(fonts, "arial.ttf"))
    _render_text(strings["shuttingDown"], fonts, os.path.join(theme, "shutting-down.png"))
    shutil.rmtree(tmp)
    shutil.rmtree(fonts)
    # cores lisas e o gradiente do painel de baixo (esticados no script)
    for name, rgb in (("top", (0, 48, 156)), ("content", (90, 126, 220)), ("black", (0, 0, 0))):
        Image.new("RGBA", (1, 1), rgb + (255,)).save(os.path.join(theme, f"{name}.png"))
    grad = Image.new("RGBA", (256, 1))
    for x in range(256):
        t = x / 255
        grad.putpixel((x, 0), tuple(round(a + (b - a) * t) for a, b in
                                    zip((57, 52, 173), (0, 48, 156))) + (255,))
    grad.save(os.path.join(theme, "bottom.png"))

    with open(os.path.join(theme, f"{THEME}.plymouth"), "w") as f:
        f.write(f"""[Plymouth Theme]
Name=Windows XP
Description=Ecrã de arranque do Windows XP (Zorin XP; imagens do ntoskrnl.exe)
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{THEME}
ScriptFile=/usr/share/plymouth/themes/{THEME}/{THEME}.script
""")
    # o GRUB limpa o ecrã a preto antes (como o tema do Zorin)
    with open(os.path.join(theme, f"{THEME}.grub"), "w") as f:
        f.write("if background_color 0,0,0; then\n  clear\nfi\n")
    with open(os.path.join(ROOT, "src", "boot", "windows-xp.script")) as f:
        script = f.read()
    for k, v in {"FADE_FRAMES": FADE_FRAMES, "STEP_FRAMES": STEP_FRAMES,
                 **{f"{n.upper()}_X": b[0] for n, b in PIECES.items()},
                 **{f"{n.upper()}_Y": b[1] for n, b in PIECES.items()},
                 **{f"BAR_{k.upper()}": v for k, v in BAR.items()}}.items():
        script = script.replace(f"@{k}@", str(v))
    with open(os.path.join(theme, f"{THEME}.script"), "w") as f:
        f.write(script)
    return theme
