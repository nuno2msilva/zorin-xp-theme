"""Ecrã de boas-vindas do XP (logonui.exe) para o ecrã de início de sessão.

Usa as imagens do logonui.exe que o UIFILE 1000 (folha de estilos DirectUI)
usa (assets/images/logon), com os nomes que a extensão do GDM espera, e
compõe nos tamanhos exatos as que o XP esticava (o St do GNOME 46 não faz
9-slice de forma fiável). Junta a extensão (src/gdm-extension) e os tipos de
letra.

Imagens (assets/images/logon; ver o UIFILE):
  glow             brilho no canto superior esquerdo (conteúdo, sem escala)
  edit             caixa da palavra-passe (borderthickness 3,3,5,5) -> 163x28
  go / go-focus    botão "ir" (seta verde) normal/com foco
  info / -focus    botão "?" (sugestão da palavra-passe)
  power / -hot     "Desligar computador" normal/rato por cima
  select           fundo do utilizador selecionado (esticado à largura da lista)
  frame / -hot     moldura da imagem normal/rato por cima ou selecionado
  picture          imagem por omissão (xadrez)
  logo             logótipo Windows XP
  divider-v / -top / -bottom   divisória vertical, linha do painel de cima,
                   linha laranja de baixo
"""
import os
import shutil

from PIL import Image

from lib import msstyles
from lib import assets
from lib.paths import ROOT

UUID = "zorin-xp-logon@zorin-xp.local"

# as que vão tal e qual (logon/<nome> -> images/<nome>.png)
PLAIN = ["glow", "go", "go-focus", "info", "info-focus", "power", "power-hot", "undock",
         "undock-hot", "frame", "frame-hot", "picture", "logo",
         "divider-v", "divider-top", "divider-bottom"]
EDIT_SIZE = (163, 28)       # edit [id=password] width=163rp; linha de 28 px
EDIT_BORDER = (3, 3, 5, 5)  # borderthickness: esquerda, cima, direita, baixo
SELECT_W = 352              # 384 - divisória 1 - margem 26 - padding 5
FONTS = ["tahoma.ttf", "tahomabd.ttf", "arial.ttf", "arialbd.ttf", "arialbi.ttf",
         "framd.ttf"]   # (título do diálogo "Desligar o computador")


def _image(name):
    """Uma imagem de assets/images, sem a cor-chave magenta (#FF00FF) do
    DirectUI quando a tem."""
    img = assets.image(name)
    # cor-chave magenta (#FF00FF) do DirectUI
    if any(img.getpixel(p)[:3] == (255, 0, 255)
           for p in ((0, 0), (img.width - 1, 0), (0, img.height - 1))):
        img = msstyles.key_out(img, (255, 0, 255))
    return img


def nine_slice(img, size, border):
    """Estica o centro e as arestas, mantém os cantos (como o DirectUI)."""
    l, t, r, b = border
    w, h = size
    sw, sh = img.size
    out = Image.new("RGBA", size)
    xs = [(0, l, 0, l), (l, sw - r, l, w - r), (sw - r, sw, w - r, w)]
    ys = [(0, t, 0, t), (t, sh - b, t, h - b), (sh - b, sh, h - b, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if sx1 > sx0 and sy1 > sy0 and dx1 > dx0 and dy1 > dy0:
                part = img.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.BILINEAR)
                out.paste(part, (dx0, dy0))
    return out


# textos do ecrã (tabela de strings do logonui.exe, na língua do XP)
# textos dos ecrãs (tabelas de strings, na língua do XP)
STRINGS = {
    "logonui.exe": {6: "password", 7: "welcome", 8: "badPassword", 10: "forgot", 11: "turnOff",
                    13: "hint", 15: "loggedOn", 22: "help", 25: "instructions", 26: "loggingOn"},
    # estados do winlogon (ecrã de boas-vindas ao entrar e ao sair)
    "winlogon.exe": {1682: "loadingSettings", 1683: "closingNetwork", 1684: "shuttingDown",
                     1687: "savingSettings", 1690: "starting", 1691: "loggingOff"},
    # dicas dos botões dos diálogos Desligar o computador / Terminar sessão
    "msgina.dll": {20129: "tipTurnOff", 20130: "tipStandby", 20132: "tipRestart"},
    "shell32.dll": {14349: "tipSwitchUser", 14350: "tipLogOff"},
}
# textos dos próprios diálogos (modelos DIALOGEX): msgina 20100 e shell32 1089
DIALOG_TEXTS = {
    ("msgina.dll", 20100): {20102: "turnOffTitle", 20104: "standby", 20103: "turnOffButton",
                            20105: "restart", 2: "cancel"},
    ("shell32.dll", 1089): {14337: "logOffTitle", 14338: "switchUser", 14339: "logOffButton"},
}


def export_strings():
    """Os textos dos ecrãs e dos diálogos (STRINGS, DIALOG_TEXTS), na língua
    de assets/locales."""
    out = {}
    for exe, ids in STRINGS.items():
        for rid, key in ids.items():
            out[key] = assets.string(exe, rid)
    for (exe, rid), ids in DIALOG_TEXTS.items():
        ctl = assets.dialog_texts(exe, rid)
        for cid, key in ids.items():
            out[key] = ctl.get(cid, "")
    return out


def export_images(out):
    os.makedirs(out, exist_ok=True)
    for name in PLAIN:
        _image(f"logon/{name}").save(os.path.join(out, name + ".png"))
    nine_slice(_image("logon/edit"), EDIT_SIZE, EDIT_BORDER).save(os.path.join(out, "edit.png"))
    sel = _image("logon/select")
    sel.resize((SELECT_W, sel.height), Image.BILINEAR).save(os.path.join(out, "select.png"))
    export_scrollbar(out)
    import json
    with open(os.path.join(os.path.dirname(out), "strings.json"), "w", encoding="utf-8") as f:
        json.dump(export_strings(), f, ensure_ascii=False, indent=1)


def build(out):
    """build/logon/<uuid>/ (extensão + imagens) e build/logon/fonts/."""
    ext = os.path.join(out, UUID)
    shutil.copytree(os.path.join(ROOT, "src", "gdm-extension", UUID), ext)
    images = os.path.join(ext, "images")
    export_images(images)
    # botão "Desligar computador": o diálogo do menu Iniciar (partilhado com a
    # extensão da sessão), os estilos dele, a caixa de aviso "Janelas" e o som
    export_dialogs(images)
    from builders import msgbox
    msgbox.export(images)
    session = os.path.join(ROOT, "src", "shell-extension", "zorin-xp@zorin-xp.local")
    shutil.copyfile(os.path.join(session, "xpDialog.js"), os.path.join(ext, "xpDialog.js"))
    # textos com as larguras de letra do XP (gdiText.js + tabela)
    shutil.copyfile(os.path.join(session, "gdiText.js"), os.path.join(ext, "gdiText.js"))
    from lib import gdimetrics
    gdimetrics.export(assets.fonts_dir(), os.path.join(ext, "gdi-metrics.json"))
    with open(os.path.join(session, "stylesheet.css"), encoding="utf-8") as f:
        css = f.read()
    block = css[css.index("/* >>> xpDialog"):css.index("/* <<< xpDialog */")]
    with open(os.path.join(ext, "stylesheet.css"), "a", encoding="utf-8") as f:
        f.write("\n" + block.replace("logon/images/", "images/"))
    os.makedirs(os.path.join(ext, "sounds"))
    shutil.copyfile(assets.sound("Windows XP Shutdown.wav"), os.path.join(ext, "sounds", "shutdown.wav"))
    fonts = os.path.join(out, "fonts")
    os.makedirs(fonts)
    from lib import fontfix
    for f in FONTS:
        src = assets.font(f)
        family = fontfix.family_of(f)
        if family:
            fontfix.fix(src, os.path.join(fonts, f), family)
        else:
            shutil.copyfile(src, os.path.join(fonts, f))
    for conf in ("60-windows-xp.conf", "61-windows-xp-arial.conf"):
        shutil.copyfile(os.path.join(ROOT, "src", "fontconfig", conf), os.path.join(out, conf))


# diálogos "Desligar o computador" (msgina) e "Terminar sessão" (shell32)
DIALOG_ICONS = {
    # tira 32x32 por estado: normal, premido, rato por cima
    "logoff/turnoff-icons": {"turnoff": 0, "standby": 3, "restart": 6},
    "logoff/logoff-icons": {"switchuser": 0, "logoff": 3},
}
ICON_STATES = ["normal", "active", "hover"]
CANCEL_SIZE = (60, 20)      # Cancelar: 40x12 DLU (Tahoma 8: 1,5 x 1,625 px)


def export_dialogs(out):
    from builders import gtkassets
    from lib import uxrender
    os.makedirs(out, exist_ok=True)
    # fundo e bandeira (versão de 16 bits; o shell32 tem cópias iguais)
    _image("logoff/background").save(os.path.join(out, "dialog-bg.png"))
    _image("logoff/flag").save(os.path.join(out, "dialog-flag.png"))
    for strip_name, icons in DIALOG_ICONS.items():
        strip = _image(strip_name)
        for name, first in icons.items():
            for i, st in enumerate(ICON_STATES):
                y = (first + i) * 32
                strip.crop((0, y, 32, y + 32)).save(os.path.join(out, f"{name}-{st}.png"))
        if strip_name == "logoff/turnoff-icons":   # Suspender indisponível
            strip.crop((0, 9 * 32, 32, 10 * 32)).save(os.path.join(out, "standby-disabled.png"))
    # botão Cancelar com o botão de comando do Luna
    ms = assets.theme("luna")
    part = ms.part("button.pushbutton")
    states = gtkassets._states(ms, "button.pushbutton", gtkassets.PUSH)
    for st, img in zip(gtkassets.PUSH, states):
        uxrender.render(img, *CANCEL_SIZE, gtkassets.margins(part)).save(
            os.path.join(out, f"button-{st}.png"))


def export_session(out):
    """Imagens e textos para a extensão da sessão (boas-vindas ao entrar,
    ecrãs de saída e diálogos de desligar/terminar sessão)."""
    export_images(os.path.join(out, "images"))
    export_dialogs(os.path.join(out, "images"))


# barra de deslocamento da lista de contas: a do tema visual (o scrollviewer do
# UIFILE usa a folha "scroller", desenhada com o uxtheme = Luna), 17 px
# (SM_CXVSCROLL); setas de 17x17 (SM_CYVSCROLL)
SCROLL_W = 17


def export_scrollbar(out):
    from builders import gtkassets
    from lib import uxrender
    ms = assets.theme("luna")
    arrows = gtkassets.fixed_glyph(ms, "ScrollBar.ArrowBtn", gtkassets.ARROWS, (SCROLL_W, SCROLL_W), "ImageFile2")
    for d in ("up", "down"):
        for st in ("normal", "hover", "active"):
            arrows[f"{d}-{st}"].save(os.path.join(out, f"scroll-{d}-{st}.png"))
    shaft = ms.part("Scrollbar.LowerTrackVert")
    img = gtkassets._states(ms, "Scrollbar.LowerTrackVert", gtkassets.FOUR)[0]
    uxrender.render(img, SCROLL_W, 40, gtkassets.margins(shaft)).save(os.path.join(out, "scroll-track.png"))
    # cursor: topo e base fixos (margens 5) e o meio esticado
    thumb = ms.part("Scrollbar.ThumbBtnVert")
    for st, img in zip(gtkassets.FOUR, gtkassets._states(ms, "Scrollbar.ThumbBtnVert", gtkassets.FOUR)):
        if st == "disabled":
            continue
        full = uxrender.render(img, SCROLL_W, 40, gtkassets.margins(thumb))
        full.crop((0, 0, SCROLL_W, 5)).save(os.path.join(out, f"scroll-thumb-top-{st}.png"))
        full.crop((0, 20, SCROLL_W, 21)).save(os.path.join(out, f"scroll-thumb-mid-{st}.png"))
        full.crop((0, 35, SCROLL_W, 40)).save(os.path.join(out, f"scroll-thumb-bottom-{st}.png"))
    for st, img in zip(gtkassets.FOUR, gtkassets._states(ms, "Scrollbar.GripperVert", gtkassets.FOUR)):
        if st != "disabled":
            img.save(os.path.join(out, f"scroll-grip-{st}.png"))
