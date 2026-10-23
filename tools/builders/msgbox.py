"""XP's "Janelas" warning box when turning off on the welcome screen.

With other sessions open, winlogon asks with a user32 MessageBox
(MB_YESNO | MB_ICONEXCLAMATION): title 710, text 713 (turn off) or 714
(restart), buttons 805/806 ("&Sim"/"&Não"). The welcome screen has no visual
style, so the box is drawn in the classic style with Luna's colours: raised
frame, gradient title with the caption font (Trebuchet MS Bold 10 pt,
smoothed), the disabled X (Marlett "r"), user32's warning icon (101) and the
text in Tahoma 8 pt without smoothing.

Everything is drawn here the way GDI does it (text glyph by glyph with the
whole v35-hinted widths, fixed-point gradient) — compared with an XP capture:
only the smoothing of a few title letters and 1 px of the "W" differ.

Runs in a separate process (FreeType reads FREETYPE_PROPERTIES when it starts):
    python3 msgbox.py <images folder>
"""
import json
import os
import subprocess
import sys

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FACE = (236, 233, 216)
LIGHT = (241, 239, 226)       # COLOR_3DLIGHT
HILIGHT = (255, 255, 255)     # COLOR_3DHILIGHT
SHADOW = (172, 168, 153)      # COLOR_3DSHADOW
DKSHADOW = (113, 111, 100)    # COLOR_3DDKSHADOW
TITLE_A = (0, 84, 227)        # COLOR_ACTIVECAPTION
TITLE_B = (61, 149, 255)      # COLOR_GRADIENTACTIVECAPTION

FRAME = 3                     # raised border (2) + window border (1)
CAPTION_H = 25                # Luna's SM_CYCAPTION; 1 px of face underneath
CLOSE = (16, 21)              # caption button; 2 px from the edges
MARGIN = 11                   # around the icon and the text (client)
TEXT_X = 62                   # text after the icon (client)
LINE_H = 13                   # Tahoma 8 pt
BTN = (75, 23)                # 50x14 DLU
BTN_GAP = 6                   # 4 DLU
BTN_SPACE = 17                # text -> buttons
RIGHT = 8                     # margem direita do texto (medida)


def _font(name, px, **kw):
    from PIL import ImageFont
    from lib import assets
    kw.setdefault("layout_engine", ImageFont.Layout.BASIC)
    return ImageFont.truetype(assets.font(name), px, **kw)


def text(img, font, s, x, y, color, mode="1"):
    """Like GDI: each glyph in its bitmap, advancing its whole width."""
    from PIL import Image
    for ch in s:
        mask, off = font.getmask2(ch, mode=mode)
        if mask.size[0]:
            m = Image.new("L", mask.size)
            m.putdata([v if mode == "L" else (255 if v else 0) for v in mask])
            img.paste(color, (x + off[0], y + off[1]), m)
        x += round(font.getlength(ch))
    return x


def advance(font, s):
    return sum(round(font.getlength(ch)) for ch in s)


def raised(img, x0, y0, x1, y1, outer=(LIGHT, DKSHADOW), inner=(HILIGHT, SHADOW)):
    """DrawEdge EDGE_RAISED (x1/y1 inclusivos)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for (tl, br), k in ((outer, 0), (inner, 1)):
        d.line([(x0 + k, y1 - k), (x0 + k, y0 + k), (x1 - k, y0 + k)], fill=tl)
        d.line([(x0 + k, y1 - k), (x1 - k, y1 - k), (x1 - k, y0 + k)], fill=br)


def button(label, state, default):
    """Classic 75x23 button: normal, default (black frame) or pressed."""
    from PIL import Image, ImageDraw
    w, h = BTN
    img = Image.new("RGB", (w, h), FACE)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 0, 0, w - 1, h - 1
    if default or state == "pressed":
        d.rectangle((x0, y0, x1, y1), outline=(0, 0, 0))
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    dx = 0
    if state == "pressed":
        d.rectangle((x0, y0, x1, y1), outline=SHADOW)
        dx = 1
    else:
        raised(img, x0, y0, x1, y1, outer=(HILIGHT, DKSHADOW), inner=(LIGHT, SHADOW))
    f = _font("tahoma.ttf", 11)
    s = label.replace("&", "")
    tx = (w - advance(f, s)) // 2 + dx
    ty = (h - LINE_H) // 2 - 1 + dx
    text(img, f, s, tx, ty, (0, 0, 0))
    return img


def box(title, body):
    """The box without the buttons (they go on top, as widgets)."""
    from PIL import Image
    from lib import assets
    f = _font("tahoma.ttf", 11)
    lines = body.replace("\r\n", "\n").split("\n")
    text_w = max(advance(f, l) for l in lines)
    text_h = len(lines) * LINE_H
    client_w = TEXT_X + text_w + RIGHT
    W = 2 * FRAME + client_w
    btn_y = MARGIN + max(32, text_h) + BTN_SPACE
    client_h = btn_y + BTN[1] + MARGIN
    H = FRAME + CAPTION_H + 1 + client_h + FRAME
    img = Image.new("RGB", (W, H), FACE)
    raised(img, 0, 0, W - 1, H - 1)

    # title: gradient up to the close button, then the final colour
    tw = W - 2 * FRAME
    span = tw - CLOSE[0] - 2
    for x in range(tw):
        c = TITLE_B if x >= span else tuple(
            a + ((((b - a) << 16) // span) * x >> 16) for a, b in zip(TITLE_A, TITLE_B))
        for y in range(CAPTION_H):
            img.putpixel((FRAME + x, FRAME + y), c)
    text(img, _font("trebucbd.ttf", 13), title, FRAME + 2, FRAME + 4, (255, 255, 255), mode="L")
    # disabled close button (MB_YESNO does not allow closing)
    cx, cy = W - FRAME - 2 - CLOSE[0], FRAME + 2
    from PIL import ImageDraw
    ImageDraw.Draw(img).rectangle((cx, cy, cx + CLOSE[0] - 1, cy + CLOSE[1] - 1), fill=FACE)
    raised(img, cx, cy, cx + CLOSE[0] - 1, cy + CLOSE[1] - 1,
           outer=(HILIGHT, DKSHADOW), inner=(LIGHT, SHADOW))
    # (Marlett is a symbol font: only the full engine uses its cmap)

    from PIL import ImageFont
    m = _font("marlett.ttf", 11, encoding="symb", layout_engine=ImageFont.Layout.RAQM)
    text(img, m, "r", cx + 4, cy + 6, HILIGHT)
    text(img, m, "r", cx + 3, cy + 5, SHADOW)

    top = FRAME + CAPTION_H + 1
    icon = assets.icon("dialog-warning", 32)
    img.paste(icon, (FRAME + MARGIN, top + MARGIN), icon)
    for i, l in enumerate(lines):
        text(img, f, l, FRAME + TEXT_X, top + MARGIN + i * LINE_H, (0, 0, 0))
    bw = 2 * BTN[0] + BTN_GAP
    layout = {"width": W, "height": H, "captionHeight": FRAME + CAPTION_H,
              "buttonsX": (W - bw) // 2 - 1, "buttonsY": top + btn_y,
              "buttonW": BTN[0], "buttonH": BTN[1], "buttonGap": BTN_GAP}
    return img, layout


def main(out):
    from lib import assets
    title = assets.string("user32", 710)
    yes, no = assets.string("user32", 805), assets.string("user32", 806)
    meta = {"yes": yes.replace("&", ""), "no": no.replace("&", ""),
            "yesKey": yes[yes.index("&") + 1].lower(), "noKey": no[no.index("&") + 1].lower()}
    for name, rid in (("shutdown", 713), ("restart", 714)):
        img, layout = box(title, assets.string("user32", rid))
        img.save(os.path.join(out, f"msgbox-{name}.png"))
        meta[name] = layout
    for key, label in (("yes", yes), ("no", no)):
        for state in ("normal", "pressed"):
            for default in (False, True):
                if state == "pressed" and not default:
                    continue
                suffix = "pressed" if state == "pressed" else ("default" if default else "normal")
                button(label, state, default).save(os.path.join(out, f"msgbox-{key}-{suffix}.png"))
    with open(os.path.join(out, "msgbox.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def export(out):
    """Gera as imagens num processo com o interpretador TrueType v35 (o do GDI)."""
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, FREETYPE_PROPERTIES="truetype:interpreter-version=35",
               PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    subprocess.run([sys.executable, os.path.abspath(__file__), out], check=True, env=env)


if __name__ == "__main__":
    main(sys.argv[1])
