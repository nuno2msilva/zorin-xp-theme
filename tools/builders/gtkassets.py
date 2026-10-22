"""Exporta os assets PNG do tema a partir do luna.msstyles.

Cada entrada declara a parte do INI, os nomes dos estados (pela ordem do
bitmap, que é a ordem dos estados do uxtheme) e como exportar:
  raw      -> cada estado tal como está (usado com border-image + slice do INI)
  fixed    -> pré-desenhado com uxrender num tamanho fixo (+ glifo centrado)
"""
import os

from PIL import Image

from lib import uxrender

FOUR = ["normal", "hover", "active", "disabled"]
PUSH = ["normal", "hover", "active", "disabled", "default"]
TOOLBAR = ["normal", "hover", "active", "disabled", "checked", "checked-hover"]
TAB = ["normal", "hover", "checked", "disabled", "focus"]
THUMB = ["normal", "hover", "active", "focus", "disabled"]
CAPTION = ["focused", "unfocused"]
CAPBTN = [f"{w}-{s}" for w in ("focused", "unfocused") for s in FOUR]
CHECK = [f"{v}-{s}" for v in ("unchecked", "checked", "mixed") for s in FOUR]
RADIO = [f"{v}-{s}" for v in ("unchecked", "checked") for s in FOUR]
ARROWS = [f"{d}-{s}" for d in ("up", "down", "left", "right") for s in FOUR]

# nome do asset, parte do INI, estados
RAW = [
    ("button", "button.pushbutton", PUSH),
    ("groupbox", "button.groupbox", ["normal"]),
    ("combo-button", "Combobox.DropDownButton", FOUR),
    ("scroll-thumb-vert", "Scrollbar.ThumbBtnVert", FOUR),
    ("scroll-thumb-horz", "Scrollbar.ThumbBtnHorz", FOUR),
    ("scroll-grip-vert", "Scrollbar.GripperVert", FOUR),
    ("scroll-grip-horz", "Scrollbar.GripperHorz", FOUR),
    ("scroll-shaft-vert", "Scrollbar.LowerTrackVert", FOUR),
    ("scroll-shaft-horz", "Scrollbar.LowerTrackHorz", FOUR),
    ("spin-up", "Spin.Up", FOUR),
    ("spin-down", "Spin.Down", FOUR),
    ("spin-right", "Spin.Uphorz", FOUR),
    ("spin-left", "Spin.Downhorz", FOUR),
    ("toolbar-button", "Toolbar.Button", TOOLBAR),
    ("toolbar-split", "Toolbar.SplitButton", TOOLBAR),
    ("toolbar-split-dropdown", "Toolbar.SplitButtonDropdown", TOOLBAR),
    ("toolbar-separator", "Toolbar.Separator", ["normal"]),
    ("toolbar-separator-vert", "Toolbar.SeparatorVert", ["normal"]),
    ("rebar", "Rebar", ["normal"]),
    ("rebar-gripper", "Rebar.Gripper", ["normal"]),
    ("status", "Status", ["normal"]),
    ("status-pane", "Status.Pane", ["normal"]),
    ("status-gripper", "Status.Gripper", ["normal", "mirrored"]),
    ("header", "Header", ["normal"]),
    ("header-item", "Header.HeaderItem", ["normal", "hover", "active", "sorted", "sorted-hover"]),
    ("progress-track", "Progress.Bar", ["normal"]),
    ("progress-track-vert", "Progress.BarVert", ["normal"]),
    ("progress-chunk", "Progress.Chunk", ["normal"]),
    ("progress-chunk-vert", "Progress.ChunkVert", ["normal"]),
    ("tab-pane", "Tab.Pane", ["normal"]),
    ("tab", "Tab.TabItem", TAB),
    ("tab-left", "Tab.TabItemLeftEdge", TAB),
    ("tab-right", "Tab.TabItemRightEdge", TAB),
    ("tab-both", "Tab.TabItemBothEdge", TAB),
    ("tab-top", "Tab.TopTabItem", TAB),
    ("tab-top-left", "Tab.TopTabItemLeftEdge", TAB),
    ("tab-top-right", "Tab.TopTabItemRightEdge", TAB),
    ("tab-top-both", "Tab.TopTabItemBothEdge", TAB),
    ("trackbar-thumb", "TrackBar.Thumb", THUMB),
    ("trackbar-thumb-vert", "TrackBar.ThumbVert", THUMB),
    ("trackbar-track", "TrackBar.Track", ["normal"]),
    ("caption", "Window.Caption", CAPTION),
    ("caption-max", "Window.MaxCaption", CAPTION),
    ("caption-small", "Window.SmallCaption", CAPTION),
    ("caption-button", "Window.MaxButton", CAPBTN),
    ("frame-left", "Window.FrameLeft", CAPTION),
    ("frame-right", "Window.FrameRight", CAPTION),
    ("frame-bottom", "Window.FrameBottom", CAPTION),
]

# Partes com vários ficheiros por DPI (ImageFile1..n): usa o de 96 ppp
DPI_PARTS = [
    ("check", "button.checkbox", CHECK, "ImageFile1"),
    ("radio", "button.radiobutton", RADIO, "ImageFile1"),
    ("trackbar-thumb-top", "TrackBar.ThumbTop", THUMB, "ImageFile1"),
    ("trackbar-thumb-bottom", "TrackBar.ThumbBottom", THUMB, "ImageFile1"),
    ("trackbar-thumb-left", "TrackBar.ThumbLeft", THUMB, "ImageFile1"),
    ("trackbar-thumb-right", "TrackBar.ThumbRight", THUMB, "ImageFile1"),
    ("tree-expander", "TreeView.Glyph", ["closed", "open"], "ImageFile1"),
    ("balloon-close", "Tooltip.Close", ["normal", "hover", "active"], "ImageFile"),
]

# Botões com glifo, pré-desenhados no tamanho fixo do XP
# nome, parte, estados, tamanho, chave do glifo
FIXED_GLYPH = [
    ("scroll-arrow", "ScrollBar.ArrowBtn", ARROWS, (17, 17), "ImageFile2"),
    ("caption-close", "Window.CloseButton", CAPBTN, (21, 21), "ImageFile3"),
    ("caption-max", "Window.MaxButton", CAPBTN, (21, 21), "ImageFile3"),
    ("caption-restore", "Window.RestoreButton", CAPBTN, (21, 21), "ImageFile3"),
    ("caption-min", "Window.MinButton", CAPBTN, (21, 21), "ImageFile3"),
    ("caption-help", "Window.HelpButton", CAPBTN, (21, 21), "ImageFile3"),
    ("caption-small-close", "Window.SmallCloseButton", CAPBTN, (13, 13), "GlyphImageFile"),
    # lista pendente: botão de 15×18 dentro do campo de 22 px (medido no XP)
    ("combo-arrow", "Combobox.DropDownButton", FOUR, (15, 18), "GlyphImageFile"),
    ("spin-left-btn", "Spin.Downhorz", FOUR, (15, 18), "GlyphImageFile"),
    ("spin-right-btn", "Spin.Uphorz", FOUR, (15, 18), "GlyphImageFile"),
]

# Glifos exportados à parte (desenhados por cima de fundos esticáveis)
GLYPHS = [
    ("combo-glyph", "Combobox.DropDownButton", FOUR),
    ("spin-up-glyph", "Spin.Up", FOUR),
    ("spin-down-glyph", "Spin.Down", FOUR),
    ("spin-right-glyph", "Spin.Uphorz", FOUR),
    ("spin-left-glyph", "Spin.Downhorz", FOUR),
]


ARROW_GLYPH_COLORS = {"normal": (0x21, 0x5D, 0xC6), "hover": (0x42, 0x8E, 0xFF),
                      "active": (0x21, 0x5D, 0xC6), "disabled": (201, 201, 194)}

# Glifos dos menus: tipo de letra Marlett a 13 px, monocromático com hinting
# (é como o USER32 os desenha; confirmado contra capturas reais do XP)
MARLETT = {"check": "a", "arrow-right": "8", "arrow-left": "7", "bullet": "h",
           "arrow-down": "6", "arrow-up": "5"}
MENU_GLYPH_COLORS = {"normal": (0, 0, 0), "selected": (255, 255, 255), "disabled": (172, 168, 153)}


def export_marlett(fonts_dir, out):
    from PIL import ImageDraw, ImageFont
    path = next(os.path.join(fonts_dir, f) for f in os.listdir(fonts_dir) if f.lower() == "marlett.ttf")
    font = ImageFont.truetype(path, 13, encoding="symb")
    for name, ch in MARLETT.items():
        mask = Image.new("1", (20, 20), 0)
        d = ImageDraw.Draw(mask)
        d.fontmode = "1"
        d.text((0, 0), chr(0xF000 + ord(ch)), font=font, fill=1)
        mask = mask.crop(mask.getbbox()).convert("L")
        for state, rgb in MENU_GLYPH_COLORS.items():
            img = Image.new("RGBA", mask.size, (*rgb, 0))
            img.putalpha(mask.point(lambda v: 255 if v else 0))
            save(img, os.path.join(out, f"menu-{name}-{state}.png"))


def export_extras(ms, out):
    # Blocos de progresso: ProgressChunkSize=6 + ProgressSpaceSize=2, altura útil 7
    # (barra de 13 px). Confirmado ao píxel contra a caixa "A copiar…" do XP.
    p = ms.part("Progress")
    size, space = int(p.get("ProgressChunkSize")), int(p.get("ProgressSpaceSize"))
    chunk = _states(ms, "Progress.Chunk", ["normal"])[0]
    c = uxrender.render(chunk, size, 7, margins(ms.part("Progress.Chunk")), tile=True)
    tile = Image.new("RGBA", (size + space, 7), (0, 0, 0, 0))
    tile.paste(c, (0, 0))
    save(tile, os.path.join(out, "progress-chunk-tile.png"))
    cv = _states(ms, "Progress.ChunkVert", ["normal"])[0]
    c = uxrender.render(cv, 7, size, margins(ms.part("Progress.ChunkVert")), tile=True)
    tile = Image.new("RGBA", (7, size + space), (0, 0, 0, 0))
    tile.paste(c, (0, space))
    save(tile, os.path.join(out, "progress-chunk-tile-vert.png"))
    # Moldura de janela (esquerda, direita, base) desenhada a 4 px pelo uxtheme,
    # num único 9-slice para o nó "decoration" das janelas CSD
    fl = _states(ms, "Window.FrameLeft", CAPTION)
    fr = _states(ms, "Window.FrameRight", CAPTION)
    fb = _states(ms, "Window.FrameBottom", CAPTION)
    for i, st in enumerate(CAPTION):
        W, H = 21, 21
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        side = H - 4
        img.alpha_composite(uxrender.render(fl[i], 4, side, margins(ms.part("Window.FrameLeft"))), (0, 0))
        img.alpha_composite(uxrender.render(fr[i], 4, side, margins(ms.part("Window.FrameRight"))), (W - 4, 0))
        img.alpha_composite(uxrender.render(fb[i], W, 4, margins(ms.part("Window.FrameBottom"))), (0, H - 4))
        save(img, os.path.join(out, f"frame-csd-{st}.png"))
        # tiras de 4 px para a extensão do GNOME Shell
        save(uxrender.render(fl[i], 4, 32, margins(ms.part("Window.FrameLeft"))), os.path.join(out, f"frame-left-strip-{st}.png"))
        save(uxrender.render(fr[i], 4, 32, margins(ms.part("Window.FrameRight"))), os.path.join(out, f"frame-right-strip-{st}.png"))
        save(uxrender.render(fb[i], 64, 4, margins(ms.part("Window.FrameBottom"))), os.path.join(out, f"frame-bottom-strip-{st}.png"))
    # Fatias de cada lado da legenda para a extensão (fixas: estão dentro das
    # margens 28/35): as 4 colunas da moldura e, nas 6 linhas de cima, mais 8
    # colunas do canto arredondado — o GTK arredonda (8 px) os cantos da
    # janela das molduras do mutter e corta aí a legenda; a extensão repõe-no
    # por cima, sem chegar aos botões (que começam na linha 6)
    cap = ms.part("Window.Caption")
    for img, st in zip(_states(ms, "Window.Caption", CAPTION), CAPTION):
        full = uxrender.render(img, 100, 30, margins(cap))
        for name, box, inner in (("left", (0, 0, 12, 30), range(4, 12)),
                                 ("right", (88, 0, 100, 30), range(0, 8))):
            side = full.crop(box)
            px = side.load()
            for y in range(6, 30):
                for x in inner:
                    px[x, y] = (0, 0, 0, 0)
            save(side, os.path.join(out, f"caption-{name}-{st}.png"))
    # Fundo das páginas com separadores (Tab.Body), usado em tamanho real
    b = ms.part("Tab.Body")
    save(ms.image(b.get("ImageFile1")), os.path.join(out, "tab-body.png"))


# O GTK não pinta o centro de um border-image ("fill" é ignorado). Para cada
# parte esticável exporta-se também <nome>-<estado>-fill.png: a parte inteira
# desenhada pelo uxrender no tamanho típico do XP, usada como fundo a 100%.
# Nesse tamanho o resultado é idêntico ao do uxtheme; noutros tamanhos o
# border-image por cima mantém cantos e bordas exatos.
FILL_REF = {
    "button": (75, 23),
    "toolbar-button": (23, 22),
    "toolbar-split": (23, 22),
    "toolbar-split-dropdown": (12, 22),
    "header-item": (80, 17),
    "header": (80, 17),
    "tab": (60, 18), "tab-left": (60, 18), "tab-right": (60, 18), "tab-both": (60, 18),
    "tab-top": (64, 21), "tab-top-left": (64, 21), "tab-top-right": (64, 21), "tab-top-both": (64, 21),
    "scroll-thumb-vert": (17, 40),
    "scroll-thumb-horz": (40, 17),
    "scroll-shaft-vert": (17, 40),
    "scroll-shaft-horz": (40, 17),
    "progress-track": (60, 13),
    "progress-track-vert": (13, 60),
    "trackbar-track": (60, 4),
    "caption": (300, 30),
    "caption-max": (300, 30),
    "caption-inner": (292, 30),
    "caption-button": (26, 21),
    "caption-small": (200, 17),
    "status": (200, 22),
    "rebar": (200, 26),
}


def center_fill(img, w, h, m, tiled):
    """Camada de fundo para o centro de um border-image.

    É o centro desenhado pelo uxtheme no tamanho de referência, prolongado
    (repetindo as linhas/colunas da orla) até cobrir a peça toda, com a
    máscara dos píxeis opacos da peça: esticada para outros tamanhos não
    arrasta contornos interiores para dentro do centro.
    """
    l, r, t, b = m
    full = uxrender.render(img, w, h, m, tile=tiled)
    cw, ch = max(1, w - l - r), max(1, h - t - b)
    center = full.crop((l, t, l + cw, t + ch))
    out = Image.new("RGBA", (w, h))
    cp, op = center.load(), out.load()
    for y in range(h):
        sy = min(max(y - t, 0), ch - 1)
        for x in range(w):
            sx = min(max(x - l, 0), cw - 1)
            op[x, y] = cp[sx, sy]
    out.putalpha(full.getchannel("A").point(lambda a: 255 if a == 255 else 0))
    return out


def margins(part):
    m = part.ints("SizingMargins") or [0, 0, 0, 0]
    return tuple(m + [0] * (4 - len(m)))


def save(img, path, scale2=True):
    img.save(path)
    if scale2:
        root, ext = os.path.splitext(path)
        img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(f"{root}@2{ext}")


def _states(ms, part_name, names, key="ImageFile", glyph=False):
    p = ms.part(part_name)
    img = ms.image(p.get(key),
                   p.flag("GlyphTransparent" if glyph else "Transparent"),
                   p.color("GlyphTransparentColor" if glyph else "TransparentColor", (255, 0, 255)))
    from lib import msstyles
    return msstyles.slice_states(img, len(names), p.get("ImageLayout", "vertical"))


def fixed_glyph(ms, part, names, size, gkey):
    """Botão com glifo desenhado no tamanho fixo do XP: {estado: imagem}."""
    from lib import msstyles
    w, h = size
    p = ms.part(part)
    bgs = _states(ms, part, names)
    gpath = p.get(gkey) or p.get("GlyphImageFile")
    gimg = ms.image(gpath, p.flag("GlyphTransparent"), p.color("GlyphTransparentColor", (255, 0, 255)))
    glyphs = msstyles.slice_states(gimg, len(names) if gimg.height % len(names) == 0 and
                                   gimg.height // len(names) <= h else 1)
    return {s: uxrender.center(uxrender.render(bgs[i], w, h, margins(p)),
                               glyphs[i] if len(glyphs) > 1 else glyphs[0])
            for i, s in enumerate(names)}


def export(ms, out, fonts_dir=None):
    os.makedirs(out, exist_ok=True)
    info = {}
    export_extras(ms, out)
    if fonts_dir:
        export_marlett(fonts_dir, out)
    for name, part, names in RAW:
        p = ms.part(part)
        if name == "status-gripper":
            img = _states(ms, part, ["normal"])[0]
            sts = [img, img.transpose(Image.FLIP_LEFT_RIGHT)]
        else:
            sts = _states(ms, part, names)
        tiled = (p.get("SizingType", "stretch") or "").strip().lower() == "tile"
        for s, img in zip(names, sts):
            save(img, os.path.join(out, f"{name}-{s}.png"))
            if name in FILL_REF:
                w, h = FILL_REF[name]
                fill = center_fill(img, w, h, margins(p), tiled)
                save(fill, os.path.join(out, f"{name}-{s}-fill.png"))
        info[name] = {"part": part, "size": sts[0].size, "margins": margins(p),
                      "fill": name in FILL_REF, "tile": tiled}
    # Legenda sem as 4 colunas de moldura de cada lado (molduras do mutter;
    # a extensão desenha essas colunas por fora da janela)
    p = ms.part("Window.Caption")
    l, r, t, b = margins(p)
    for s, img in zip(CAPTION, _states(ms, "Window.Caption", CAPTION)):
        inner = img.crop((4, 0, img.width - 4, img.height))
        save(inner, os.path.join(out, f"caption-inner-{s}.png"))
        w, h = FILL_REF["caption-inner"]
        fill = center_fill(inner, w, h, (l - 4, r - 4, t, b), False)
        save(fill, os.path.join(out, f"caption-inner-{s}-fill.png"))
    info["caption-inner"] = {"part": "Window.Caption", "size": (img.width - 8, img.height),
                             "margins": (l - 4, r - 4, t, b), "fill": True, "tile": False}
    # Legenda dividida em duas (vistas divididas do libadwaita, como as
    # Definições: barra lateral + conteúdo, cada um com a sua barra): metade
    # esquerda só com o canto esquerdo e metade direita só com o direito,
    # para as duas formarem uma única legenda contínua
    for s, img in zip(CAPTION, _states(ms, "Window.Caption", CAPTION)):
        halves = {"caption-split-left": (img.crop((0, 0, img.width - r, img.height)), (l, 0, t, b)),
                  "caption-split-right": (img.crop((l, 0, img.width, img.height)), (0, r, t, b))}
        for name, (half, m) in halves.items():
            save(half, os.path.join(out, f"{name}-{s}.png"))
            save(center_fill(half, 300, 30, m, False), os.path.join(out, f"{name}-{s}-fill.png"))
            info[name] = {"part": "Window.Caption", "size": half.size, "margins": m,
                          "fill": True, "tile": False}
    for name, part, names, key in DPI_PARTS:
        sts = _states(ms, part, names, key)
        for s, img in zip(names, sts):
            save(img, os.path.join(out, f"{name}-{s}.png"))
        info[name] = {"part": part, "size": sts[0].size, "margins": (0, 0, 0, 0)}
    # Moldura dos separadores sem a linha de cima (GTK4: essa linha passa a ser
    # a borda de baixo do cabeçalho, para o separador selecionado a tapar)
    pane = _states(ms, "Tab.Pane", ["normal"])[0]
    save(pane.crop((0, 1, pane.width, pane.height)), os.path.join(out, "tab-pane-notop.png"))
    for name, part, names, size, gkey in FIXED_GLYPH:
        for s, img in fixed_glyph(ms, part, names, size, gkey).items():
            save(img, os.path.join(out, f"{name}-{s}.png"))
        # (o botão Maximizar chama-se como a legenda maximizada, "caption-max":
        # não substituir as medidas da legenda, que o CSS usa em {{part:…}})
        info.setdefault(name, {"part": part, "size": size, "margins": margins(ms.part(part))})
    # Setas soltas, sem botão: o glifo das setas das barras de deslocamento
    # (9×9) nos azuis das ligações do painel de tarefas do Explorador
    # (shellstyle.dll: #215DC6, #428EFF ao passar o rato)
    from lib import msstyles
    p = ms.part("ScrollBar.ArrowBtn")
    glyphs = msstyles.slice_states(ms.image(p.get("ImageFile2"), True, (255, 0, 255)), 16)
    for d, i in (("up", 0), ("down", 4), ("left", 8), ("right", 12)):
        for s, col in ARROW_GLYPH_COLORS.items():
            g = glyphs[i].copy()
            g.putdata([(*col, a) if a else (0, 0, 0, 0) for *_rgb, a in g.getdata()])
            save(g, os.path.join(out, f"arrow-glyph-{d}-{s}.png"))
    for name, part, names in GLYPHS:
        p = ms.part(part)
        gimg = ms.image(p.get("GlyphImageFile"), p.flag("GlyphTransparent"),
                        p.color("GlyphTransparentColor", (255, 0, 255)))
        from lib import msstyles
        n = len(names) if gimg.height % len(names) == 0 else 1
        gl = msstyles.slice_states(gimg, n)
        for i, s in enumerate(names):
            save(gl[i if n > 1 else 0], os.path.join(out, f"{name}-{s}.png"))
    return info


# --------------------------------------------------------------------------
# Explorador do Windows (para o Nautilus, src/nautilus-xp): botões da barra
# de ferramentas (shell32, ícones de 24 px com alfa), "Ir para" e o painel de
# tarefas (shellstyle.dll do Luna azul)
# --------------------------------------------------------------------------
EXPLORER_TB = {"back": 0, "forward": 1, "up": 28, "search": 17, "folders": 43, "views": 32}


def _disabled(img):
    """Botão inativo das barras de ferramentas do XP: o ícone em cinzento,
    aclarado (o círculo verde de Retroceder fica a ~173, medido), opaco."""
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            v = int(0.3 * r + 0.59 * g + 0.11 * b)
            v = 255 - (255 - v) * 3 // 5
            px[x, y] = (v, v, v, a)
    return out


def export_explorer(ms, out):
    """Peças do Explorador do XP para o Ficheiros (src/nautilus-xp): botões da
    barra, "Ir para", ícones das tarefas e das confirmações, a bandeira
    animada e o painel de tarefas do tema (ms: o tema, assets.theme)."""
    from lib import msstyles
    from lib import assets
    os.makedirs(out, exist_ok=True)
    normal = assets.image("explorer/toolbar")
    hot = assets.image("explorer/toolbar-hot")
    for name, i in EXPLORER_TB.items():
        box = (i * 24, 0, i * 24 + 24, 24)
        save(normal.crop(box), os.path.join(out, f"explorer-{name}-normal.png"))
        save(hot.crop(box), os.path.join(out, f"explorer-{name}-hot.png"))
        save(_disabled(normal.crop(box)), os.path.join(out, f"explorer-{name}-disabled.png"))
    for st, name in (("normal", "explorer/go"), ("hot", "explorer/go-hot")):
        img = assets.image(name)
        if img.getpixel((0, 0))[:3] == (255, 0, 255):
            img = msstyles.key_out(img, (255, 0, 255))
        save(img, os.path.join(out, f"explorer-go-{st}.png"))
    # setinha das listas pendentes da barra de ferramentas: 5×3 (medida)
    for st, col in (("normal", (0, 0, 0, 255)), ("disabled", (172, 168, 153, 255))):
        arrow = Image.new("RGBA", (5, 3), (0, 0, 0, 0))
        for y, (x0, x1) in enumerate(((0, 4), (1, 3), (2, 2))):
            for x in range(x0, x1 + 1):
                arrow.putpixel((x, y), col)
        save(arrow, os.path.join(out, f"explorer-dropdown-{st}.png"))
    # ponto e visto dos menus em 13×13 (o GTK4 estica a imagem ao tamanho
    # do elemento): o glifo do XP ao centro, sem ser esticado
    for glyph in ("menu-bullet", "menu-check"):
        for st in ("normal", "selected", "disabled"):
            src = os.path.join(out, f"{glyph}-{st}.png")
            if not os.path.exists(src):
                continue
            g = Image.open(src).convert("RGBA")
            box = Image.new("RGBA", (13, 13), (0, 0, 0, 0))
            box.alpha_composite(g, ((13 - g.width) // 2, (13 - g.height) // 2))
            save(box, os.path.join(out, f"{glyph}13-{st}.png"))
    # ícones das tarefas do painel (16 px): nova pasta, mudar o nome, mover,
    # copiar, eliminar, reproduzir, apresentação, fundo
    for name, icon in (("new-folder", "folder-new"), ("rename", "task-rename"), ("move", "task-move"),
                       ("copy", "task-copy"), ("delete", "edit-delete"), ("play", "media-playback-start"),
                       ("slideshow", "task-slideshow"), ("background", "desktop")):
        ic = assets.icon(icon, 16)
        if ic is not None:
            save(ic.convert("RGBA"), os.path.join(out, f"explorer-task-{name}.png"))
    # confirmação de eliminação (32 px, os dos diálogos 1011-1013 do shell32:
    # ficheiro, pasta, vários) e o aviso das caixas de mensagem. (Mandar para
    # a Reciclagem mostra o ícone da própria Reciclagem, vazia ou cheia; os
    # dos diálogos são os de eliminar de vez.)
    for name, icon in (("confirm-file", "delete-file"), ("confirm-folder", "delete-folder"),
                       ("confirm-many", "delete-many"), ("warning", "dialog-warning"),
                       ("bin-empty", "recycle-bin"), ("bin-full", "recycle-bin-full")):
        ic = assets.icon(icon, 32)
        if ic is not None:
            save(ic.convert("RGBA"), os.path.join(out, f"explorer-{name}.png"), scale2=False)
    # bandeira do Windows no canto da barra de menus: 50 fotogramas de 22×22
    # (o 1.º é a imagem parada; anima enquanto a pasta carrega)
    save(assets.image("explorer/brand"), os.path.join(out, "explorer-brand.png"), scale2=False)

    def bmp(name):
        return msstyles.key_out(ms.shell(name), (255, 0, 255))
    # cabeçalho das secções (186×21, esticado) e setas de recolher/abrir
    save(bmp("section-header"), os.path.join(out, "explorer-section-header.png"))
    # secções especiais (Música, Imagens, Vídeos): cabeçalho azul, setas, ícone
    # de 32 px, marca de água da secção (60 px, pintada sobre (237,242,255):
    # passa a branco com alfa) e da vista (150 px, sobre branco)
    save(bmp("special-header"), os.path.join(out, "explorer-special-header.png"))
    for name in ("collapse", "collapse-hot", "expand", "expand-hot"):
        save(bmp(f"special-{name}"), os.path.join(out, f"explorer-special-{name}.png"))
    for kind in ("music", "pictures", "videos"):
        save(bmp(f"{kind}-icon"), os.path.join(out, f"explorer-{kind}-icon.png"))
        wm = bmp(f"{kind}-section")
        px = wm.load()
        for y in range(wm.height):
            for x in range(wm.width):
                r, g, b, _a = px[x, y]
                a = max(0, min(255, round(((r - 237) / 18 + (g - 242) / 13) / 2 * 255)))
                px[x, y] = (255, 255, 255, a)
        save(wm, os.path.join(out, f"explorer-{kind}-section.png"))
        save(bmp(f"{kind}-view"), os.path.join(out, f"explorer-{kind}-view.png"))
    for name in ("collapse", "collapse-hot", "expand", "expand-hot"):
        save(bmp(f"section-{name}"), os.path.join(out, f"explorer-section-{name}.png"))
