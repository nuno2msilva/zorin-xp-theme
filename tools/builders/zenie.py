"""Zen Browser com o aspeto do Internet Explorer 6 do XP (src/zen-ie).

Imagens, todas dos binários do XP:
  shell32.dll  bitmaps 204/205 — botões de 24 px do IE6 Luna (normal / rato
               por cima): retroceder, avançar, parar, atualizar, página
               inicial, procurar, favoritos, imprimir, tamanho do texto,
               editar, ferramentas, multimédia, histórico, correio, ecrã
               inteiro, discussão. Os desativados fazem-se como o comctl32
               (cinzentos, mais claros).
  shell32.dll  bitmap 240 — a bandeira do XP animada (50 imagens de 22 px
               sobre branco; a primeira é a parada).
  shell32.dll  bitmaps 230/231 — botão verde "Ir para" (20 px).
  inetcpl.cpl  ícone 1313 (zona Internet, na barra de estado).
  iexplore.exe ícone 32529 (página do IE: caixa de
               endereço e "Concluído", como na captura).
  luna.msstyles (via gtk-assets do tema GTK) — botões da barra de
               ferramentas, fundo da barra de bandas (Rebar: os 13 px esticados
               sem suavizar a 86 px, com as 4 linhas de baixo fixas — igual à
               captura), botão da caixa de combinação.
  Screenshots/ie6-referencia.png (captura do IE6 da VM do utilizador) — a
               barra de estado (fundo, divisórias, pega, barra de progresso),
               que o IE desenha por cima do fundo do tema com outras cores.

Texto: "ZXP Tahoma" (tools/lib/pixelfont.py), a Tahoma 8 do XP em píxeis com as
larguras do GDI — o Firefox não usa as larguras ajustadas e com a Tahoma
normal as letras ficam com espaços irregulares.

Sons: extensão src/zen-ie/sounds com o clique do XP ("Iniciar navegação",
Media/Windows XP Start.wav) e os da barra de informações do SP2 (Windows XP
Pop-up Blocked.wav, Windows XP Information Bar.wav).

Barras Favoritos e Histórico do IE6: extensões src/zen-ie/favorites e
src/zen-ie/history (+ explorerbar/ comum), com os ícones da barra do
Explorador: shdocvw.dll 534/535 (Adicionar, Organizar, Ver; 18x16, magenta =
transparente), browseui.dll 563/564 (Procurar), shdocvw.dll ícone 20783 (dias
do histórico), shell32.dll ícones 4/5 (pastas), os botões do XP do msstyles.

Página de erro de rede: a do IE6 (shdoclc.dll, DNSERROR.HTM), tools/ieerror.py.

build(xp_root, gtk_assets, out) -> out/zorin-xp-ie/{ie.css, content.css, img/*.png},
                                   out/fonts/ZXPTahoma{,-Bold,13-Bold}.ttf, ZXPVerdanaIE.ttf,
                                   out/zorin-xp-ie-sounds@zorin-xp.local.xpi
"""
import base64
import os
import re
import shutil
import subprocess
import zipfile

from PIL import Image, ImageEnhance

import sys
# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import msstyles
from lib.paths import ROOT
from lib import pixelfont
from lib import winicons
from lib import assets

IE_BUTTONS = ["back", "forward", "stop", "refresh", "home", "search", "favorites", "print",
              "font", "edit", "tools", "media", "history", "mail", "fullscreen", "discuss"]
LUNA = ["toolbar-button-hover", "toolbar-button-active", "toolbar-button-checked",
        "toolbar-button-checked-hover", "toolbar-split-dropdown-hover",
        "toolbar-split-dropdown-active", "toolbar-separator-normal", "rebar-normal",
        "status-gripper-normal", "progress-track-normal", "progress-chunk-normal",
        "combo-button-normal", "combo-button-hover", "combo-button-active",
        "combo-glyph-normal", "combo-glyph-hover", "combo-glyph-active",
        "check-unchecked-normal", "check-unchecked-hover", "check-checked-normal", "check-checked-hover",
        "button-normal", "button-hover", "button-active", "button-default",
        "caption-focused-fill",
        # moldura de janela Luna dos diálogos das páginas (alert/confirm/prompt)
        "caption-left-focused", "caption-right-focused", "frame-left-strip-focused",
        "frame-right-strip-focused", "frame-bottom-strip-focused",
        "caption-close-focused-normal", "caption-close-focused-hover", "caption-close-focused-active"]


def disabled(im):
    """Botão desativado como na captura do IE (cinzento claro, sem cor)."""
    gray = ImageEnhance.Color(im).enhance(0.0)
    gray = ImageEnhance.Contrast(gray).enhance(0.55)
    gray = ImageEnhance.Brightness(gray).enhance(1.18)
    gray.putalpha(im.getchannel("A"))
    return gray


def build(gtk_assets, out):
    dst = os.path.join(out, "zorin-xp-ie")
    img = os.path.join(dst, "img")
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(img)
    shutil.copyfile(os.path.join(ROOT, "src", "zen-ie", "ie.css"), os.path.join(dst, "ie.css"))

    fonts = os.path.join(out, "fonts")
    shutil.rmtree(fonts, ignore_errors=True)
    for ttf, px, family, style, name in (
            ("tahoma.ttf", 11, "ZXP Tahoma", "Regular", "ZXPTahoma.ttf"),
            ("tahomabd.ttf", 11, "ZXP Tahoma", "Bold", "ZXPTahoma-Bold.ttf"),
            # nome do espaço na barra lateral: Tahoma negrito 10 pt
            ("tahomabd.ttf", 13, "ZXP Tahoma 13", "Bold", "ZXPTahoma13-Bold.ttf")):
        pixelfont.export(assets.font(ttf), px, family, style, os.path.join(fonts, name))
    # página de erro do IE (tools/builders/ieerror.py): a Verdana 8 pt com o negrito e o
    # título (13 pt) numa só fonte; as larguras ficam no .json (não se instala)
    pixelfont.export_mix(assets.font("verdana.ttf"), assets.font("verdanab.ttf"), 11, 17, "ZXP Verdana IE",
                         os.path.join(fonts, "ZXPVerdanaIE.ttf"))
    import json
    from builders import ieerror
    widths = os.path.join(fonts, "ZXPVerdanaIE.json")
    page = ieerror.css(json.load(open(widths)))
    os.remove(widths)
    with open(os.path.join(ROOT, "src", "zen-ie", "content.css"), encoding="utf-8") as f:
        content = f.read()
    dx, dy, dw, dh = page["detect"]
    for key, value in (("ZXP-ERROR-TEXT", page["text"]), ("ZXP-ERROR-LINKS", page["links"]),
                       ("ZXP-ERROR-ICONS", page["icons"]), ("ZXP-ERROR-BG", page["background"]),
                       ("ZXP-DETECT-LEFT", str(dx - 2)), ("ZXP-DETECT-TOP", str(dy)),
                       ("ZXP-DETECT-WIDTH", str(dw + 4)), ("ZXP-DETECT-HEIGHT", str(dh))):
        content = content.replace(key, value)
    with open(os.path.join(dst, "content.css"), "w", encoding="utf-8") as f:
        f.write(content)

    # extensão dos sons (o XPI é um zip com o manifesto na raiz): o clique e os
    # da barra de informações do SP2
    src = os.path.join(ROOT, "src", "zen-ie", "sounds")
    oggs = {}
    for wav_name, ogg_name in (("windows xp start.wav", "start.ogg"),
                               ("windows xp pop-up blocked.wav", "popup-blocked.ogg"),
                               ("windows xp information bar.wav", "infobar.ogg")):
        wav = assets.sound(wav_name)
        # (o Zen não toca WAV: vão em OGG Vorbis, convertidos com o ffmpeg)
        oggs[ogg_name] = os.path.join(out, ogg_name)
        # (bitexact e número de série fixo: o mesmo .ogg em cada construção)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis",
                        "-q:a", "6", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                        "-serial_offset", "1", oggs[ogg_name]], check=True)
    with zipfile.ZipFile(os.path.join(out, "zorin-xp-ie-sounds@zorin-xp.local.xpi"), "w",
                         zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(src)):
            z.write(os.path.join(src, f), f)
        for name, path in oggs.items():
            z.write(path, name)
            os.remove(path)
    # a pasta do "Guardar como" lembrada por sítio (src/zen-ie/lastdir), o
    # aviso de novo separador (src/zen-ie/tabflash), o pino da barra dos
    # separadores (src/zen-ie/sidebarpin), o título do IE (src/zen-ie/title)
    # e as barras de deslocamento do XP (src/zen-ie/scrollbars)
    for name in ("lastdir", "tabflash", "sidebarpin", "title", "scrollbars"):
        src = os.path.join(ROOT, "src", "zen-ie", name)
        with zipfile.ZipFile(os.path.join(out, f"zorin-xp-ie-{name}@zorin-xp.local.xpi"), "w",
                             zipfile.ZIP_DEFLATED) as z:
            for f in sorted(os.listdir(src)):
                z.write(os.path.join(src, f), f)

    normal = assets.image("ie/toolbar")
    hot = assets.image("ie/toolbar-hot")
    # ícone do diálogo "Adicionar aos Favoritos" (estrela com +, 24 px: o 4.º
    # botão da barra do Explorador)
    assets.image("explorer/toolbar").crop((3 * 24, 0, 4 * 24, 24)).save(os.path.join(img, "add-favorite.png"))
    # a pasta dos favoritos (a lista "Pasta" do mesmo diálogo)
    assets.icon("folder", 16).save(os.path.join(img, "folder.png"))
    for i, name in enumerate(IE_BUTTONS):
        box = (i * 24, 0, i * 24 + 24, 24)
        normal.crop(box).save(os.path.join(img, f"tb-{name}.png"))
        hot.crop(box).save(os.path.join(img, f"tb-{name}-hot.png"))
        disabled(normal.crop(box)).save(os.path.join(img, f"tb-{name}-disabled.png"))

    assets.image("explorer/brand").convert("RGB").save(os.path.join(img, "throbber.png"))
    for name in ("go", "go-hot"):
        assets.image(f"explorer/{name}").save(os.path.join(img, f"{name}.png"))

    assets.icon("ie-zone-internet", 16).save(os.path.join(img, "zone-internet.png"))
    # cadeado da barra de estado (ligação segura): shdocvw.dll 103, da família
    # dos ícones dos painéis (100 página inicial, 112 ocupado, 116 a imprimir)
    assets.icon("ie-status-lock", 16).save(os.path.join(img, "status-lock.png"))
    # barra de informações do SP2 (xpsp2res.dll): pop-up bloqueado (5410) e o
    # aviso pequeno (16) para os outros avisos e pedidos de permissão
    assets.icon("ie-popup-blocked", 16).save(os.path.join(img, "popup-blocked.png"))
    assets.icon("ie-infobar-warning", 16).save(os.path.join(img, "infobar-warning.png"))
    # caixas de mensagem das páginas: aviso (alert) e pergunta (confirm), user32
    assets.icon("dialog-warning", 32).save(os.path.join(img, "mb-warning.png"))
    assets.icon("dialog-question", 32).save(os.path.join(img, "mb-question.png"))
    assets.icon("ie-page", 16).save(os.path.join(img, "page.png"))

    rebar(gtk_assets, img)
    statusbar(img)
    tab_buttons(img)
    # transferências (em baixo na barra lateral): o ícone de transferência do
    # IE (shdocvw.dll 113, o da barra de estado: disco com a seta vermelha)
    assets.icon("ie-downloads", 16).save(os.path.join(img, "downloads.png"))
    # "Limpar" (fechar os separadores não fixos): a Limpeza do disco do XP
    assets.icon("cleanmgr", 16).save(os.path.join(img, "clear-tabs.png"))
    # × do título das barras do Explorador (Favoritos/Histórico): 7x7, traço de 2 px
    x = Image.new("RGBA", (16, 14))
    for i in range(7):
        for dx in (0, 1):
            for px, py in ((4 + i + dx, 3 + i), (10 - i + dx, 3 + i)):
                if 4 <= px <= 11:
                    x.putpixel((px, py), (0, 0, 0, 255))
    x.save(os.path.join(img, "ebar-close.png"))
    # "+" (Novo separador/espaço/pasta): a mesma espessura do × (traço de 2 px)
    plus = Image.new("RGBA", (16, 16))
    for i in range(8):
        for d in (0, 1):
            plus.putpixel((4 + i, 7 + d), (0, 0, 0, 255))
            plus.putpixel((7 + d, 4 + i), (0, 0, 0, 255))
    plus.save(os.path.join(img, "plus.png"))
    # o separador novo a piscar: o botão da barra de tarefas do XP que pede
    # atenção (TaskBand.FlashButton, margens de 4 px)
    luna = assets.theme("luna")
    luna.states("TaskBand.FlashButton")[0].convert("RGBA").save(os.path.join(img, "flash-button.png"))
    # barras de deslocamento das páginas: as imagens do tema GTK (ScrollBar
    # do Luna, as mesmas do Explorador) embutidas na folha "agent" que a
    # extensão src/zen-ie/scrollbars regista
    def embed(m):
        data = open(os.path.join(gtk_assets, f"{m.group(1)}.png"), "rb").read()
        return 'url("data:image/png;base64,%s")' % base64.b64encode(data).decode()
    template = open(os.path.join(ROOT, "src", "zen-ie", "scrollbars.css.in"), encoding="utf-8").read()
    with open(os.path.join(os.path.dirname(img), "scrollbars.css"), "w", encoding="utf-8") as f:
        f.write(re.sub(r"\{\{img:([\w-]+)\}\}", embed, template))
    # o pino da barra dos separadores: o das barras do Explorador do Luna
    # (ExplorerBar.HeaderPin: 0 deitado, 3 espetado) sem cor, em cinzentos
    pins = luna.states("ExplorerBar.HeaderPin")
    for name, i in (("pin-in", 3), ("pin-out", 0)):
        src = pins[i].convert("RGBA")
        im = Image.new("RGBA", src.size)
        for y in range(src.height):
            for x in range(src.width):
                r, g, b, a = src.getpixel((x, y))
                if a >= 128:
                    v = (r * 299 + g * 587 + b * 114) // 1000
                    im.putpixel((x, y), (v, v, v, 255))
        im.save(os.path.join(img, f"{name}.png"))
    # o leitor de som como o Windows Media Player 9 do XP (wmploc.dll, o leitor
    # embutido: OCXLAYOUTFULL): a barra prateada (371, linhas 29-63) e os
    # botões redondos, que trazem o fundo da barra à altura a que ficavam nela
    # (reproduzir/pausa na linha 32 -> 3 px; os outros na 37 -> 8 px)
    assets.image("wmp/bar").crop((0, 29, 44, 64)).save(os.path.join(img, "wmp-bar.png"))
    for name in ("play", "pause", "prev", "next", "mute"):
        for state in ("", "-hover", "-down", "-disabled"):
            # (a pausa não tem imagem desativada: fica a normal)
            src = f"wmp/{name}{state}" if (name, state) != ("pause", "-disabled") else "wmp/pause"
            assets.image(src).save(os.path.join(img, f"wmp-{name}{state}.png"))
    # seta dos botões com menu (Retroceder/Avançar): triângulo 5x3 como na captura
    for name, color in (("arrow", (0, 0, 0, 255)), ("arrow-disabled", (0xc9, 0xc9, 0xc2, 255))):
        a = Image.new("RGBA", (5, 3))
        for y, (x0, x1) in enumerate(((0, 5), (1, 4), (2, 3))):
            for x in range(x0, x1):
                a.putpixel((x, y), color)
        a.save(os.path.join(img, f"{name}.png"))
    for name in LUNA:
        for suffix in ("", "-fill"):
            src = os.path.join(gtk_assets, f"{name}{suffix}.png")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(img, f"{name}{suffix}.png"))
    explorer_bars(gtk_assets, img, out)
    return dst


def rebar(gtk_assets, img):
    """Fundo das bandas: a imagem do msstyles (320x13, com gradiente nas duas
    direções) esticada sem suavizar à janela — em altura só as 9 linhas de
    cima (as 4 de baixo ficam fixas: igual à captura)."""
    src = Image.open(os.path.join(gtk_assets, "rebar-normal.png")).convert("RGB")
    src.crop((0, 0, src.width, src.height - 4)).save(os.path.join(img, "rebar-top.png"))
    src.crop((0, src.height - 4, src.width, src.height)).save(os.path.join(img, "rebar-bottom.png"))
    # (o título das barras do Explorador e os 3 px por baixo dos botões: só a
    # 1.ª linha, esticada — o degradê da esquerda para a direita)
    src.crop((0, 0, src.width, 1)).save(os.path.join(img, "rebar-row.png"))


def tab_buttons(img):
    """Fechar / descarregar nos separadores: só o desenho, a preto, como o ×
    do título das barras do Explorador do IE (7x7, traço de 2 px) e um – da
    mesma espessura; o realce ao passar o rato é o dos botões planos do XP."""
    x = Image.new("RGBA", (13, 13))
    for i in range(7):
        for dx in (0, 1):
            for px, py in ((3 + i + dx, 3 + i), (9 - i + dx, 3 + i)):
                if 3 <= px <= 10:
                    x.putpixel((px, py), (0, 0, 0, 255))
    x.save(os.path.join(img, "tab-close.png"))
    m = Image.new("RGBA", (13, 13))
    for px in range(3, 10):
        for py in (6, 7):
            m.putpixel((px, py), (0, 0, 0, 255))
    m.save(os.path.join(img, "tab-unload.png"))


def _strip18(name, i):
    """O botão i (18x16) de uma tira das barras do Explorador, sem o magenta."""
    im = msstyles.key_out(assets.image(name), (255, 0, 255))
    return im.crop((i * 18, 0, i * 18 + 18, 16))


def explorer_bars(gtk_assets, img, out):
    """XPIs das barras Favoritos e Histórico (ver o cabeçalho)."""
    shared = {
        "img/page.png": assets.icon("ie-page", 16),
        "img/folder.png": assets.icon("folder", 16),
        "img/folder-open.png": assets.icon("folder-open", 16),
        "img/history-day.png": assets.icon("ie-history-day", 16),
    }
    n16 = assets.image("ie/toolbar-small")
    extra = {
        "favorites": {
            "img/ebar-add.png": _strip18("ie/explorer-bar", 0), "img/ebar-add-hot.png": _strip18("ie/explorer-bar-hot", 0),
            "img/ebar-organize.png": _strip18("ie/explorer-bar", 1), "img/ebar-organize-hot.png": _strip18("ie/explorer-bar-hot", 1),
            "img/tb-favorites-16.png": n16.crop((6 * 16, 0, 7 * 16, 16)),
            "img/ebar-add-icon.png": Image.open(os.path.join(img, "add-favorite.png")),
        },
        "history": {
            "img/ebar-view.png": _strip18("ie/explorer-bar", 2), "img/ebar-view-hot.png": _strip18("ie/explorer-bar-hot", 2),
            "img/ebar-search.png": _strip18("ie/search-bar", 0), "img/ebar-search-hot.png": _strip18("ie/search-bar-hot", 0),
            "img/tb-history-16.png": n16.crop((12 * 16, 0, 13 * 16, 16)),
        },
        # (a janela Localizar não usa a barra do Explorador, só as imagens)
        "find": {"img/tb-search-16.png": n16.crop((5 * 16, 0, 6 * 16, 16))},
    }
    copies = {f"img/{n}.png": os.path.join(img, f"{n}.png") for n in
              ("rebar-top", "rebar-bottom", "rebar-row", "toolbar-button-hover", "toolbar-button-active", "arrow")}
    copies["img/tb-favorites.png"] = os.path.join(img, "tb-favorites.png")
    copies["img/tb-history.png"] = os.path.join(img, "tb-history.png")
    for n in ("button-normal", "button-hover", "button-active", "button-default", "button-disabled",
              "check-unchecked-normal", "check-unchecked-hover", "check-checked-normal", "check-checked-hover",
              "check-unchecked-disabled", "radio-unchecked-normal", "radio-unchecked-hover", "radio-checked-normal", "radio-checked-hover"):
        copies[f"img/{n}.png"] = os.path.join(gtk_assets, f"{n}.png")
    copies["img/tb-search.png"] = os.path.join(img, "tb-search.png")
    common = os.path.join(ROOT, "src", "zen-ie", "explorerbar")
    import io
    for name in ("favorites", "history", "find"):
        src = os.path.join(ROOT, "src", "zen-ie", name)
        xpi = os.path.join(out, f"zorin-xp-ie-{name}@zorin-xp.local.xpi")
        with zipfile.ZipFile(xpi, "w", zipfile.ZIP_DEFLATED) as z:
            for d in ((src, common) if name != "find" else (src,)):
                for f in sorted(os.listdir(d)):
                    z.write(os.path.join(d, f), f)
            for arc, path in copies.items():
                z.write(path, arc)
            for arc, im in {**shared, **extra[name]}.items():
                buf = io.BytesIO()
                im.save(buf, "PNG")
                z.writestr(arc, buf.getvalue())


def statusbar(img):
    ref = Image.open(os.path.join(ROOT, "Screenshots", "ie6-referencia.png")).convert("RGB")
    y0, y1 = 910, 933                      # 23 px
    ref.crop((1300, y0, 1301, y1)).save(os.path.join(img, "status-bg.png"))
    ref.crop((1488, y0, 1490, y1)).save(os.path.join(img, "status-sep.png"))
    ref.crop((1898, y0, 1915, y1)).save(os.path.join(img, "status-gripper.png"))
    # barra de progresso vazia (as colunas dos blocos tapadas com uma do meio)
    bar = ref.crop((1493, y0, 1586, y1))
    mid = bar.crop((50, 0, 51, bar.height))
    for x in range(4, 40):
        bar.paste(mid, (x, 0))
    bar.save(os.path.join(img, "progress.png"))
    # botão da lista da caixa de endereço (15x18, dentro do rebordo)
    ref.crop((1828, 96, 1843, 114)).save(os.path.join(img, "combo-drop.png"))
    # tira de 11 blocos verdes (cada um: bloco + intervalo, 8 px), só as linhas
    # dos blocos (y 917..927): entra da esquerda bloco a bloco
    chunk = ref.crop((1497, 917, 1505, 928))
    strip = Image.new("RGB", (88, chunk.height))
    for i in range(11):
        strip.paste(chunk, (i * 8, 0))
    strip.save(os.path.join(img, "progress-chunks.png"))


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1], sys.argv[2]))
