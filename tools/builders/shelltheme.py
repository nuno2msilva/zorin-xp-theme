"""Tema do GNOME Shell: barra de tarefas, botão Iniciar e menu Zorin à XP.

Parte do tema Shell do Zorin instalado no sistema (para tudo o resto do
Shell continuar coerente com as extensões do Zorin) e acrescenta-lhe
src/shell/xp.css, com os elementos pré-desenhados a partir do luna.msstyles
nas medidas confirmadas contra capturas reais do XP.
"""
import os
import shutil

from PIL import Image

from lib import msstyles
from lib.paths import ROOT
from lib import uxrender
from lib import assets
from lib import xpdraw

ZORIN_SHELL = "/usr/share/themes/ZorinBlue-Light/gnome-shell"

TASKBAR_H = 30
TASKBAND_W = 160
START_LABEL_ID = 578            # explorer.exe: o texto do botão Iniciar


def _m(ms, part):
    v = ms.part(part).ints("SizingMargins") or [0, 0, 0, 0]
    return tuple(v)


def start_button(ms, out):
    """Os 3 estados do botão Iniciar (normal, rato por cima, premido), com o
    texto da língua desenhado como o XP o desenha. Devolve a largura.

    O botão é um Button do comctl32 com a classe "Start::Button" do tema:
    a bandeira (explorer.exe, bitmap 143) e o texto (string 578: "Iniciar",
    "start" no XP inglês) dentro das ContentMargins, o texto com a letra, a
    cor e a sombra "continuous" do tema (lib/xpdraw). A largura é a do texto
    mais as margens, a bandeira e 2 px: "Iniciar" (51 px) dá 112, "start"
    (38 px) dá 99, a largura do StartButton.bmp. A janela do botão começa 1 px
    antes do ecrã e desce 2 px abaixo dele: vê-se de x = 1 e as 30 linhas de cima.
    Igual às capturas reais (reference/start-button), menos 2 píxeis do "I"
    (o hinting do FreeType põe um ponto do "I" 1/64 px ao lado do do XP).
    """
    part = ms.part("Start::Button")
    label = assets.string("explorer", START_LABEL_ID)
    font = xpdraw.theme_font(part.get("Font"), assets.font_named)
    left, right, top, bottom = part.ints("ContentMargins")
    flag = assets.image("taskbar/start-flag")
    win_w, win_h = font.extent(label) + left + right + flag.width + 2, TASKBAR_H + 2
    width = win_w - 1
    # (no ecrã: tudo 1 px à esquerda do que está na janela)
    content = (left - 1, top, win_w - right - 1, win_h - bottom)
    flag_xy = (content[0], (content[1] + content[3] - flag.height) // 2)
    text_rect = (content[0] + flag.width,) + content[1:]
    bg = uxrender.render(ms.states("TaskBar.BackgroundBottom")[0], width, TASKBAR_H,
                         _m(ms, "TaskBar.BackgroundBottom"), tile=True)
    for state, img_state in zip(("normal", "hover", "active"), ms.states("Start::Button")):
        img = bg.copy()
        button = uxrender.render(img_state, win_w, win_h, _m(ms, "Start::Button"))
        img.alpha_composite(button.crop((1, 0, win_w, TASKBAR_H)))
        xpdraw.draw_image(img, flag, flag_xy)
        xpdraw.draw_shadow_text(img, text_rect, label, font, part.color("TextColor"),
                                part.color("TextShadowColor"), *part.ints("TextShadowOffset"))
        img.save(os.path.join(out, f"start-{state}.png"))
    return width


def taskbar_assets(ms, out):
    # Fundo (TaskBar.BackgroundBottom): largo o suficiente para qualquer ecrã
    bgm = _m(ms, "TaskBar.BackgroundBottom")
    strip = uxrender.render(ms.states("TaskBar.BackgroundBottom")[0], 50, TASKBAR_H, bgm, tile=True)
    wide = Image.new("RGBA", (7680, TASKBAR_H))
    for x in range(0, wide.width, strip.width):
        wide.paste(strip, (x, 0))
    wide.save(os.path.join(out, "taskbar-bg.png"))
    # Botões de janela 160×30: 0 normal, 1 hover, 2/4 ativo, 3/5 ativo + hover
    tb = ms.states("TaskBand::Toolbar.Button")
    tm = _m(ms, "TaskBand::Toolbar.Button")
    for idx, name in ((0, "normal"), (1, "hover"), (4, "active"), (5, "active-hover"), (2, "pressed")):
        uxrender.render(tb[idx], TASKBAND_W, TASKBAR_H, tm).save(os.path.join(out, f"taskband-{name}.png"))
    # Área de notificação, já à altura da barra (só se estica na horizontal)
    tray = ms.states("TrayNotifyHoriz::TrayNotify.Background")[0]
    uxrender.render(tray, 300, TASKBAR_H, _m(ms, "TrayNotifyHoriz::TrayNotify.Background")).save(
        os.path.join(out, "tray.png"))
    # Seta "mostrar ícones ocultos" (19×20, tamanho real): fechada "<" e aberta ">",
    # cada uma normal / rato por cima / premida
    for part, kind in (("TrayNotifyHoriz::Button", "closed"), ("TrayNotifyHorizOpen::Button", "open")):
        for state, img in zip(("normal", "hover", "active"), ms.states(part)):
            img.save(os.path.join(out, f"tray-chevron-{kind}-{state}.png"))


# Larguras do menu Iniciar (o XP usa 380 = 190 + 190); as peças são desenhadas
# pelo uxrender a esta largura. startmenu.js usa os mesmos valores.
START_W, LEFT_W = 380, 190
HEADER_H, FOOTER_H = 64, 41    # UserPane 64; Logoff medido em captura real: 41


def startmenu_xp(ms, out):
    """Peças do menu Iniciar do XP pré-desenhadas nos tamanhos do XP."""
    def r(part, w, h, i=0, tile=False):
        return uxrender.render(ms.states(part)[i], w, h, _m(ms, part), tile=tile)
    r("StartPanel.UserPane", START_W, HEADER_H).save(os.path.join(out, "start-header.png"))
    r("StartPanel.Logoff", START_W, FOOTER_H).save(os.path.join(out, "start-footer.png"))
    # Fundos das colunas (incluem a linha laranja, as bordas laterais e a divisória)
    r("StartPanel.ProgList", LEFT_W, 1200).save(os.path.join(out, "start-left.png"))
    r("StartPanel.PlacesList", START_W - LEFT_W, 1200).save(os.path.join(out, "start-right.png"))
    r("StartPanel.MorePrograms", LEFT_W, 30).save(os.path.join(out, "start-more-bg.png"))
    ms.states("StartPanel.MoreProgramsArrow")[0].save(os.path.join(out, "start-more-arrow.png"))
    ms.states("StartPanel.MoreProgramsArrow(hot)")[0].save(os.path.join(out, "start-more-arrow-hot.png"))
    # "Voltar" (não existe no XP): a mesma seta, espelhada
    for part, suffix in (("StartPanel.MoreProgramsArrow", ""), ("StartPanel.MoreProgramsArrow(hot)", "-hot")):
        ms.states(part)[0].transpose(Image.FLIP_LEFT_RIGHT).save(
            os.path.join(out, f"start-back-arrow{suffix}.png"))
    # Moldura da fotografia do utilizador (UserTileBackground), 48 px + margens de conteúdo
    tile = ms.part("StartPanel.UserPicture")
    cl, cr, ct, cb = tile.ints("ContentMargins")
    r("StartPanel.UserPicture", 48 + cl + cr, 48 + ct + cb).save(os.path.join(out, "start-usertile.png"))
    # Ícones de sessão (24×24): 0 ejetar, 1 terminar sessão, 2 encerrar
    for part, suffix in (("StartPanel.LogoffButtons", ""), ("StartPanel.LogoffButtons(hot)", "-hot")):
        strip = ms.states(part)[0]
        for k, name in ((1, "logoff"), (2, "shutdown")):
            strip.crop((k * 24, 0, k * 24 + 24, 24)).save(os.path.join(out, f"start-{name}{suffix}.png"))
    # Ícones da coluna direita (24 px nativos do XP, como no menu Iniciar real:
    # Os meus documentos 235, imagens 236, música 237, O meu computador 16,
    # Painel de controlo 22 — identificados ao píxel numa captura do XP)
    # (sem 24 px no XP: o maior reduzido, como no tema de ícones)
    from builders import icons
    for key, name in {
        "computer": "computer", "desktop": "desktop",
        "documents": "folder-documents", "music": "folder-music",
        "pictures": "folder-pictures", "videos": "folder-videos",
        "programs": "add-remove-programs", "settings": "control-panel",
        "appearance": "appearance-and-themes", "terminal": "cmd",
        "internet": "internet", "help": "help-and-support",
        # Downloads (o XP não tinha): o mesmo ícone da pasta do tema de ícones
        "downloads": "composite:downloads",
    }.items():
        icons.image(name, 24).save(os.path.join(out, f"start-ico-{key}.png"))
    for part, name in (("StartPanel.ProgListSeparator", "start-sep-left"),
                       ("StartPanel.PlacesListSeparator", "start-sep-right")):
        ms.states(part)[0].save(os.path.join(out, f"{name}.png"))
    start_shadow().save(os.path.join(out, "start-shadow.png"))


# Sombra do menu Iniciar (CS_DROPSHADOW). Não está no tema: é o win32k que a
# desenha. Medida numa captura real (Screenshot_20261011172149): 5 px à direita
# e em baixo, preto com estas opacidades por distância à borda; o canto de baixo
# usa a maior das duas distâncias; no topo direito (canto arredondado) e no
# fundo esquerdo a sombra vai aparecendo como abaixo.
SHADOW_ALPHA = (0.44, 0.33, 0.17, 0.055, 0.01)
SHADOW_TOP_RIGHT = (   # distância por linha (a contar do topo do menu) e coluna; 0 = sem sombra
    (5, 5, 0, 0, 0), (4, 5, 5, 0, 0), (4, 4, 5, 5, 0), (3, 4, 4, 5, 0),
    (3, 3, 4, 5, 5), (2, 3, 4, 4, 5), (2, 3, 3, 4, 5), (2, 2, 3, 4, 5),
)
SHADOW_TOP, SHADOW_LEFT = 6, 10   # linhas sem sombra no topo; colunas do esbatimento à esquerda


def start_shadow():
    """Imagem 9-slice (border-image 15 5 5 10) para um menu de 11×16."""
    n = len(SHADOW_ALPHA)
    top = SHADOW_TOP + len(SHADOW_TOP_RIGHT) + 1
    mw, mh = SHADOW_LEFT + 1, top + 1
    img = Image.new("RGBA", (mw + n, mh + n), (0, 0, 0, 0))

    def put(x, y, d):
        if 1 <= d <= n:
            img.putpixel((x, y), (0, 0, 0, round(SHADOW_ALPHA[d - 1] * 255)))
    for c in range(n):
        for y in range(mh):
            k = y - SHADOW_TOP
            if k >= 0:
                put(mw + c, y, SHADOW_TOP_RIGHT[k][c] if k < len(SHADOW_TOP_RIGHT) else c + 1)
        for r in range(n):
            put(mw + c, mh + r, max(c, r) + 1)
    for x in range(mw):
        start = max(1, SHADOW_LEFT - x)    # x=9 total, x=8 a partir de 2, ...
        for r in range(n):
            put(x, mh + r, max(start, r + 1) if start <= n else 0)
    return img


SCROLL_W = 17   # SM_CXVSCROLL do XP


def scrollbar_assets(ms, out):
    """Barra de deslocamento vertical do XP para o St (StScrollBar).

    O St não tem botões de seta: a barra leva padding de 17 px em cima e em
    baixo e uma border-image (17 0 17 0) com as setas e a calha; startmenu.js
    trata dos cliques e troca a imagem conforme a seta está realçada/premida.
    """
    from builders import gtkassets
    arrows = gtkassets.fixed_glyph(ms, "ScrollBar.ArrowBtn", gtkassets.ARROWS, (SCROLL_W, SCROLL_W), "ImageFile2")
    shaft = gtkassets._states(ms, "Scrollbar.LowerTrackVert", gtkassets.FOUR)[0]
    track = uxrender.render(shaft, SCROLL_W, 20, _m(ms, "Scrollbar.LowerTrackVert"))
    for name, up, down in (("normal", "up-normal", "down-normal"),
                           ("up-hover", "up-hover", "down-normal"), ("up-active", "up-active", "down-normal"),
                           ("down-hover", "up-normal", "down-hover"), ("down-active", "up-normal", "down-active")):
        img = Image.new("RGBA", (SCROLL_W, 2 * SCROLL_W + track.height))
        img.alpha_composite(arrows[up], (0, 0))
        img.alpha_composite(track, (0, SCROLL_W))
        img.alpha_composite(arrows[down], (0, SCROLL_W + track.height))
        img.save(os.path.join(out, f"scroll-vbar-{name}.png"))
    # cursor (ThumbBtnVert, margens 5) e pega (GripperVert, centrada)
    thumbs = gtkassets._states(ms, "Scrollbar.ThumbBtnVert", gtkassets.FOUR)
    grips = gtkassets._states(ms, "Scrollbar.GripperVert", gtkassets.FOUR)
    for i, s in enumerate(("normal", "hover", "active")):
        uxrender.render(thumbs[i], SCROLL_W, 40, _m(ms, "Scrollbar.ThumbBtnVert")).save(
            os.path.join(out, f"scroll-thumb-{s}.png"))
        grips[i].save(os.path.join(out, f"scroll-grip-{s}.png"))


# Ícones da área de notificação do XP (16 px), para os indicadores do sistema:
# volume do systray (stobject.dll), microfone (o de mão com balão do painel
# Fala, sapi.cpl — só está na dllcache), localização (o XP não tinha: o globo
# das Opções regionais, intl.cpl), rede — no XP a rede
# sem fios usa o mesmo ícone dos dois monitores (netshell.dll) —, Bluetooth
# (irprops.cpl) e a tira da bateria do medidor de energia (batmeter.dll, 10
# estados de 16 px com magenta como cor-chave)
# ícones da área de notificação: tray-ico-<chave>.png <- assets/icons
TRAY_ICONS = {
    "volume": "tray-volume", "volume-muted": "tray-volume-muted",
    "mic": "tray-mic",
    "location": "regional-options",
    # dois monitores: apagados, o da frente aceso a enviar, o de trás a
    # receber, ambos — como o XP mostrava a atividade
    "network": "tray-network", "network-tx": "tray-network-tx",
    "network-rx": "tray-network-rx", "network-txrx": "network-wired",
    "network-off": "tray-network-off",
    "network-busy": "tray-network-busy",
    "bluetooth": "tray-bluetooth",
}
BATTERY_STRIP = {0: "battery-full", 1: "battery-half", 2: "battery-low", 3: "battery-missing",
                 4: "battery-unknown", 5: "battery-empty", 8: "battery-ac"}


def tray_icons(out):
    for key, name in TRAY_ICONS.items():
        assets.icon(name, 16).save(os.path.join(out, f"tray-ico-{key}.png"))
    strip = msstyles.key_out(assets.image("taskbar/battery-icons"), (255, 0, 255))
    for k, key in BATTERY_STRIP.items():
        strip.crop((k * 16, 0, k * 16 + 16, 16)).save(os.path.join(out, f"tray-ico-{key}.png"))


def startmenu_assets(ms, out):
    """Moldura do menu: tampa superior azul (StartUserPanel), inferior
    (StartPanelLogoff), separadores e fundos das duas colunas."""
    startmenu_xp(ms, out)
    W = 64
    top = uxrender.render(ms.states("StartPanel.UserPane")[0], W, 64, _m(ms, "StartPanel.UserPane"))
    bottom = uxrender.render(ms.states("StartPanel.Logoff")[0], W, 40, _m(ms, "StartPanel.Logoff"))
    frame = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    frame.alpha_composite(top.crop((0, 0, W, 8)), (0, 0))
    frame.alpha_composite(bottom.crop((0, 40 - 8, W, 40)), (0, W - 8))
    # laterais: as colunas exteriores da tampa superior (linhas abaixo dos cantos)
    left = top.crop((0, 40, 3, 41)).resize((3, W - 16), Image.NEAREST)
    right = top.crop((W - 3, 40, W, 41)).resize((3, W - 16), Image.NEAREST)
    frame.alpha_composite(left, (0, 8))
    frame.alpha_composite(right, (W - 3, 8))
    frame.save(os.path.join(out, "startmenu-frame.png"))
    for part, name in (("StartPanel.ProgListSeparator", "startmenu-sep-left"),
                       ("StartPanel.PlacesListSeparator", "startmenu-sep-right")):
        ms.states(part)[0].save(os.path.join(out, f"{name}.png"))
    arrow = ms.states("StartPanel.MoreProgramsArrow")[0]
    arrow.save(os.path.join(out, "startmenu-more-arrow.png"))
    ms.states("StartPanel.MoreProgramsArrow(hot)")[0].save(os.path.join(out, "startmenu-more-arrow-hot.png"))


def build(out_dir, name="WindowsXP-Luna"):
    """Tema do GNOME Shell em out_dir/<name>/gnome-shell."""
    ms = assets.theme("luna")
    shell = os.path.join(out_dir, name, "gnome-shell")
    if os.path.isdir(ZORIN_SHELL):
        shutil.copytree(ZORIN_SHELL, shell, ignore=shutil.ignore_patterns("*.gresource"))
    else:
        os.makedirs(shell)
        open(os.path.join(shell, "gnome-shell.css"), "w").close()
    xp = os.path.join(shell, "xp")
    os.makedirs(xp, exist_ok=True)
    taskbar_assets(ms, xp)
    start_button_w = start_button(ms, xp)
    startmenu_assets(ms, xp)
    scrollbar_assets(ms, xp)
    tray_icons(xp)
    base = open(os.path.join(shell, "gnome-shell.css")).read()
    extra = open(os.path.join(ROOT, "src", "shell", "xp.css")).read()
    for k, v in {"START_BUTTON_W": start_button_w,
                 "START_W": START_W, "LEFT_W": LEFT_W, "RIGHT_W": START_W - LEFT_W}.items():
        extra = extra.replace("{{%s}}" % k, str(v))
    with open(os.path.join(shell, "gnome-shell.css"), "w") as f:
        f.write(base + "\n\n/* ====== Zorin XP ====== */\n" + extra)
    return shell
