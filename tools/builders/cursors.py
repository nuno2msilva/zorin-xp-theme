"""Tema Xcursor com os cursores do esquema "Predefinição do Windows" do XP.

Os cursores estão em assets/cursors (um .cur por cursor, extraídos das DLL
do sistema: ver tools/catalog.py). Aqui ganham o halo dos píxeis de
inversão, a sombra do XP, as versões a 2x e os nomes alternativos.
"""
import os
import struct

from PIL import Image, ImageFilter

from lib import assets

# nome Xcursor principal (= assets/cursors/<nome>.cur, origem em
# tools/catalog.py) e os outros nomes que apontam para ele
CURSORS = [
    ("default", ["left_ptr", "arrow", "top_left_arrow", "context-menu",
                 "zoom-in", "zoom-out", "grab", "openhand", "x-cursor", "X_cursor"]),
    ("text", ["xterm", "ibeam"]),
    ("wait", ["watch"]),
    ("crosshair", ["cross", "tcross", "cross_reverse", "diamond_cross", "cell", "plus"]),
    ("up-arrow", ["center_ptr", "sb_up_arrow"]),
    ("nwse-resize", ["size_fdiag", "nw-resize", "se-resize", "top_left_corner",
                     "bottom_right_corner", "bd_double_arrow"]),
    ("nesw-resize", ["size_bdiag", "ne-resize", "sw-resize", "top_right_corner",
                     "bottom_left_corner", "fd_double_arrow"]),
    ("ew-resize", ["size_hor", "sb_h_double_arrow", "e-resize", "w-resize",
                   "left_side", "right_side", "h_double_arrow"]),
    ("ns-resize", ["size_ver", "sb_v_double_arrow", "n-resize", "s-resize",
                   "top_side", "bottom_side", "v_double_arrow", "double_arrow"]),
    ("move", ["fleur", "size_all", "grabbing", "closedhand", "dnd-none"]),
    ("not-allowed", ["crossed_circle", "forbidden", "circle"]),
    ("progress", ["left_ptr_watch", "half-busy"]),
    ("help", ["question_arrow", "whats_this", "left_ptr_help", "dnd-ask"]),
    ("pencil", []),
    ("pointer", ["hand", "hand1", "hand2", "pointing_hand"]),
    ("all-scroll", []),
    ("n-scroll", []),
    ("s-scroll", []),
    ("w-scroll", []),
    ("e-scroll", []),
    ("nw-scroll", []),
    ("ne-scroll", []),
    ("se-scroll", []),
    ("sw-scroll", []),
    ("ns-scroll", []),       # deslocamento automático só vertical
    ("ew-scroll", []),       # ... só horizontal
    ("dnd-move", []),
    ("copy", ["dnd-copy"]),
    ("alias", ["dnd-link", "link"]),
    ("no-drop", ["dnd-no-drop"]),
    ("col-resize", ["split_h", "sb_h_double_arrow_bar"]),
    ("row-resize", ["split_v"]),
    ("vertical-text", []),
]


# Nomes legados (hashes de cursores X11 usados por Qt/Mozilla)
LEGACY_HASHES = {
    "pointer": ["e29285e634086352946a0e7090d73106", "9d800788f1b08800ae810202380a0822"],
    "copy": ["1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
             "b66166c04f8c3109214a4fbd64a50fc8"],
    "alias": ["3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f",
              "a2a266d0498c3104214a47bd64ab0fc8"],
    "dnd-move": ["4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"],
    "help": ["5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"],
    "progress": ["08e8e1c95fe2fc01f976f1e063a24ccd", "3ecb610c1bf2410f44200f48c40d3599"],
    "col-resize": ["14fef782d02440884392942c11205230"],
    "row-resize": ["2870a09082c103050810ffdffffe0204"],
    "not-allowed": ["03b6e0fcb3499374a867c041f52298f0"],
    "ew-resize": ["028006030e0e7ebffc7f7070c0600140"],
    "ns-resize": ["00008160000006810000408080010102"],
    "nwse-resize": ["c7088f0f3e6c8088236ef8e1e3e70000"],
    "nesw-resize": ["fcf1c3c7cd4491d801f1e1c78f100000"],
}


def drop_shadow(img, offset=(2, 2), blur=1.0, opacity=0.35):
    """Sombra do ponteiro (SPI_SETCURSORSHADOW, ativa por omissão no XP).

    Parâmetros aproximados — o algoritmo do win32k não está documentado.
    A sombra só se desloca para a direita e para baixo (sem dar a volta à
    imagem: o ImageChops.offset fazia aparecer uma faixa por cima do cursor).
    """
    alpha = img.getchannel("A").point(lambda v: int(v * opacity))
    shifted = Image.new("L", img.size, 0)
    shifted.paste(alpha.crop((0, 0, img.width - offset[0], img.height - offset[1])), offset)
    if blur:
        shifted = shifted.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(shifted)
    sh.alpha_composite(img)
    return sh


def invert_halo(img, inverted):
    """Os píxeis de inversão (o I do texto, a cruz) não existem no Xcursor:
    ficam pretos (como sobre fundos claros) com um contorno branco de 1 px, para
    se verem também sobre fundos escuros, como a inversão do XP permite."""
    if not inverted:
        return img
    out = img.copy()
    px = out.load()
    w, h = img.size
    for x, y in inverted:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] == 0:
                    px[nx, ny] = (255, 255, 255, 255)
    return out


def xcursor_bytes(images):
    """images: [(PIL RGBA, (hotx, hoty), nominal_size, delay_ms)] -> ficheiro Xcursor."""
    ntoc = len(images)
    out = bytearray(struct.pack("<4sIII", b"Xcur", 16, 0x10000, ntoc))
    pos = 16 + ntoc * 12
    chunks = []
    for img, (hx, hy), size, delay in images:
        w, h = img.size
        px = bytearray()
        for r, g, b, a in img.getdata():
            px += struct.pack("<I", (a << 24) | ((r * a // 255) << 16) | ((g * a // 255) << 8) | (b * a // 255))
        chunk = struct.pack("<IIIIIIIII", 36, 0xFFFD0002, size, 1, w, h, hx, hy, delay) + px
        out += struct.pack("<III", 0xFFFD0002, size, pos)
        chunks.append(chunk)
        pos += len(chunk)
    for c in chunks:
        out += c
    return bytes(out)


def build(out_dir, name="WindowsXP", shadow=True, scales=(1, 2)):
    """Tema Xcursor em out_dir/<name>, com os cursores de assets/cursors."""
    theme = os.path.join(out_dir, name)
    cdir = os.path.join(theme, "cursors")
    os.makedirs(cdir, exist_ok=True)
    with open(os.path.join(theme, "index.theme"), "w") as f:
        # (nomes que o XP não tem: os do Adwaita, em vez do cursor antigo do X11)
        f.write("[Icon Theme]\nName=Windows XP\nComment=Cursores predefinidos do Windows XP\n"
                "Inherits=Adwaita\n")
    for main, aliases in CURSORS:
        img, hot = assets.cursor(main)[0]
        img = invert_halo(img, getattr(img, "inverted", None))
        if shadow:
            img = drop_shadow(img)
        frames = []
        for s in scales:
            im = img if s == 1 else img.resize((img.width * s, img.height * s), Image.NEAREST)
            frames.append((im, (hot[0] * s, hot[1] * s), 32 * s, 0))
        with open(os.path.join(cdir, main), "wb") as f:
            f.write(xcursor_bytes(frames))
        for a in aliases + LEGACY_HASHES.get(main, []):
            p = os.path.join(cdir, a)
            if not os.path.lexists(p):
                os.symlink(main, p)
    return theme
