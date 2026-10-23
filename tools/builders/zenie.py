"""Zen Browser with the look of XP's Internet Explorer 6 (src/zen-ie).

Images, all from XP's binaries:
  shell32.dll  bitmaps 204/205 — IE6 Luna 24 px buttons (normal / hover):
               back, forward, stop, refresh, home, search, favorites,
               print, text size, edit, tools, media, history, mail, full
               screen, discuss. The disabled ones are made like comctl32
               does (grey, lighter).
  shell32.dll  bitmap 240 — the animated XP flag (50 images of 22 px on
               white; the first one is the still one).
  shell32.dll  bitmaps 230/231 — green "Go" button (20 px).
  inetcpl.cpl  icon 1313 (Internet zone, in the status bar).
  iexplore.exe icon 32529 (IE page: address box and "Concluído", as in
               the capture).
  luna.msstyles (through the GTK theme's gtk-assets) — toolbar buttons,
               band bar background (Rebar: the 13 px stretched without
               smoothing to 86 px, with the bottom 4 rows fixed — identical to
               the capture), combo box button.
  assets/captures/ie6 (cropped from an IE6 capture in the user's VM) — the
               status bar (background, dividers, grip, progress bar), which
               IE draws over the theme's background with other colours.

Text: "ZXP Tahoma" (tools/lib/pixelfont.py), XP's Tahoma 8 in pixels with
GDI's widths — Firefox does not use the hinted widths and with the normal
Tahoma the letters are irregularly spaced.

The extension (one, zorin-xp-ie@zorin-xp.local, with a Preferences page that
turns each feature on and off: src/zen-ie/extension) gathers the features
below; each lives in its folder of src/zen-ie and goes to the extension's root
(pages and scripts) or to experiments/<name>/ (privileged parts).

Sounds: src/zen-ie/sounds, with XP's click ("Iniciar
navegação", Media/Windows XP Start.wav) and SP2's information bar ones
(Windows XP Pop-up Blocked.wav, Windows XP Information Bar.wav).

IE6 Favorites and History bars: src/zen-ie/favorites and src/zen-ie/history
(+ the shared explorerbar/), in the extension's one side bar, with the
Explorer bar icons: shdocvw.dll 534/535 (Add, Organize, View; 18x16, magenta
= transparent), browseui.dll 563/564 (Search), shdocvw.dll icon 20783
(history days), shell32.dll icons 4/5 (folders), XP's buttons from msstyles.

Network error page: IE6's (shdoclc.dll, DNSERROR.HTM), tools/builders/ieerror.py.

build(gtk_assets, out) -> out/zorin-xp-ie/{ie.css, content.css, img/*.png},
                          out/fonts/ZXPTahoma{,-Bold,13-Bold}.ttf, ZXPVerdanaIE.ttf,
                          out/zorin-xp-ie@zorin-xp.local.xpi
"""
import base64
import os
import re
import shutil
import subprocess
import zipfile

from PIL import Image, ImageEnhance

import sys
# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import msstyles
from lib.paths import ROOT
from lib import pixelfont
from lib import winicons
from lib import assets

# the extensions of earlier versions, now all in zorin-xp-ie@zorin-xp.local
OLD_EXTENSIONS = [f"zorin-xp-ie-{n}@zorin-xp.local" for n in
                  ("sounds", "favorites", "history", "find", "lastdir", "tabflash", "sidebarpin", "title",
                   "scrollbars")]
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
        # Luna window frame of the page dialogs (alert/confirm/prompt)
        "caption-left-focused", "caption-right-focused", "frame-left-strip-focused",
        "frame-right-strip-focused", "frame-bottom-strip-focused",
        "caption-close-focused-normal", "caption-close-focused-hover", "caption-close-focused-active"]


def disabled(im):
    """Disabled button as in the IE capture (light grey, no colour)."""
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
            # name of the space in the sidebar: Tahoma bold 10 pt
            ("tahomabd.ttf", 13, "ZXP Tahoma 13", "Bold", "ZXPTahoma13-Bold.ttf")):
        pixelfont.export(assets.font(ttf), px, family, style, os.path.join(fonts, name))
    # IE error page (tools/builders/ieerror.py): Verdana 8 pt with the bold and
    # the heading (13 pt) in one font; the widths go in the .json (not installed)
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

    # the IE sounds (src/zen-ie/sounds): the click and SP2's information bar
    # ones, which go into the extension (extension())
    oggs = {}
    for wav_name, ogg_name in (("windows xp start.wav", "start.ogg"),
                               ("windows xp pop-up blocked.wav", "popup-blocked.ogg"),
                               ("windows xp information bar.wav", "infobar.ogg")):
        wav = assets.sound(wav_name)
        # (Zen does not play WAV: they go as OGG Vorbis, converted with ffmpeg)
        oggs[ogg_name] = os.path.join(out, ogg_name)
        # (bitexact and a fixed serial number: the same .ogg on every build)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis",
                        "-q:a", "6", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                        "-serial_offset", "1", oggs[ogg_name]], check=True)

    normal = assets.image("ie/toolbar")
    hot = assets.image("ie/toolbar-hot")
    # icon of the "Adicionar aos Favoritos" dialog (star with +, 24 px: the 4th
    # button of the Explorer bar)
    assets.image("explorer/toolbar").crop((3 * 24, 0, 4 * 24, 24)).save(os.path.join(img, "add-favorite.png"))
    # the favorites folder (the "Pasta" list of the same dialog)
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
    # status bar padlock (secure connection): shdocvw.dll 103, from the family
    # of the panel icons (100 home page, 112 busy, 116 printing)
    assets.icon("ie-status-lock", 16).save(os.path.join(img, "status-lock.png"))
    # SP2's information bar (xpsp2res.dll): pop-up blocked (5410) and the small
    # warning (16) for the other notices and permission requests
    assets.icon("ie-popup-blocked", 16).save(os.path.join(img, "popup-blocked.png"))
    assets.icon("ie-infobar-warning", 16).save(os.path.join(img, "infobar-warning.png"))
    # page message boxes: warning (alert) and question (confirm), user32
    assets.icon("dialog-warning", 32).save(os.path.join(img, "mb-warning.png"))
    assets.icon("dialog-question", 32).save(os.path.join(img, "mb-question.png"))
    assets.icon("ie-page", 16).save(os.path.join(img, "page.png"))

    rebar(gtk_assets, img)
    statusbar(img)
    tab_buttons(img)
    # downloads (at the bottom of the sidebar): IE's download icon (shdocvw.dll
    # 113, the status bar one: disk with the red arrow)
    assets.icon("ie-downloads", 16).save(os.path.join(img, "downloads.png"))
    # "Limpar" (close the unpinned tabs): XP's Disk Cleanup
    assets.icon("cleanmgr", 16).save(os.path.join(img, "clear-tabs.png"))
    # × of the Explorer bars' title (Favorites/History): 7x7, 2 px stroke
    x = Image.new("RGBA", (16, 14))
    for i in range(7):
        for dx in (0, 1):
            for px, py in ((4 + i + dx, 3 + i), (10 - i + dx, 3 + i)):
                if 4 <= px <= 11:
                    x.putpixel((px, py), (0, 0, 0, 255))
    x.save(os.path.join(img, "ebar-close.png"))
    # "+" (New tab/space/folder): the same thickness as the × (2 px stroke)
    plus = Image.new("RGBA", (16, 16))
    for i in range(8):
        for d in (0, 1):
            plus.putpixel((4 + i, 7 + d), (0, 0, 0, 255))
            plus.putpixel((7 + d, 4 + i), (0, 0, 0, 255))
    plus.save(os.path.join(img, "plus.png"))
    # the flashing new tab: XP's taskbar button asking for attention
    # (TaskBand.FlashButton, 4 px margins)
    luna = assets.theme("luna")
    luna.states("TaskBand.FlashButton")[0].convert("RGBA").save(os.path.join(img, "flash-button.png"))
    # page scrollbars: the GTK theme's images (Luna's ScrollBar, the same as the
    # Explorer's) embedded in the "agent" sheet the src/zen-ie/scrollbars
    # extension registers
    def embed(m):
        data = open(os.path.join(gtk_assets, f"{m.group(1)}.png"), "rb").read()
        return 'url("data:image/png;base64,%s")' % base64.b64encode(data).decode()
    template = open(os.path.join(ROOT, "src", "zen-ie", "scrollbars.css.in"), encoding="utf-8").read()
    with open(os.path.join(os.path.dirname(img), "scrollbars.css"), "w", encoding="utf-8") as f:
        f.write(re.sub(r"\{\{img:([\w-]+)\}\}", embed, template))
    # the tab bar pin: the one of Luna's Explorer bars (ExplorerBar.HeaderPin:
    # 0 lying, 3 pushed in) without colour, in greys
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
    # the sound player like XP's Windows Media Player 9 (wmploc.dll, the
    # embedded player: OCXLAYOUTFULL): the silver bar (371, rows 29-63) and
    # the round buttons, which carry the bar's background at the height they
    # had on it (play/pause at row 32 -> 3 px; the others at 37 -> 8 px)
    assets.image("wmp/bar").crop((0, 29, 44, 64)).save(os.path.join(img, "wmp-bar.png"))
    for name in ("play", "pause", "prev", "next", "mute"):
        for state in ("", "-hover", "-down", "-disabled"):
            # (pause has no disabled image: the normal one stays)
            src = f"wmp/{name}{state}" if (name, state) != ("pause", "-disabled") else "wmp/pause"
            assets.image(src).save(os.path.join(img, f"wmp-{name}{state}.png"))
    # arrow of the buttons with a menu (Back/Forward): 5x3 triangle as in the capture
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
    extension(gtk_assets, img, out, oggs)
    return dst


def rebar(gtk_assets, img):
    """Band background: the msstyles image (320x13, with a gradient in both
    directions) stretched to the window without smoothing — vertically only
    the top 9 rows (the bottom 4 stay fixed: identical to the capture)."""
    src = Image.open(os.path.join(gtk_assets, "rebar-normal.png")).convert("RGB")
    src.crop((0, 0, src.width, src.height - 4)).save(os.path.join(img, "rebar-top.png"))
    src.crop((0, src.height - 4, src.width, src.height)).save(os.path.join(img, "rebar-bottom.png"))
    # (the Explorer bars' title and the 3 px below the buttons: only the first
    # row, stretched — the left-to-right gradient)
    src.crop((0, 0, src.width, 1)).save(os.path.join(img, "rebar-row.png"))


def tab_buttons(img):
    """Close / unload on the tabs: only the drawing, in black, like the × of
    the IE Explorer bars' title (7x7, 2 px stroke) and a – of the same
    thickness; the hover highlight is XP's flat buttons'."""
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
    """Button i (18x16) of a strip of the Explorer bars, without the magenta."""
    im = msstyles.key_out(assets.image(name), (255, 0, 255))
    return im.crop((i * 18, 0, i * 18 + 18, 16))


def extension(gtk_assets, img, out, oggs):
    """The extension, zorin-xp-ie@zorin-xp.local.xpi (see the header): the
    core (src/zen-ie/extension: manifest, background, Preferences page,
    experiments/settings and experiments/buttons) at the root, with the
    features' pages and scripts; their privileged parts in experiments/<name>/;
    the images and the sounds."""
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
        # (the Find window does not use the Explorer bar, only the images)
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
    images = {**shared, **extra["favorites"], **extra["history"], **extra["find"]}
    # the extension's icon (about:addons): IE's page, iexplore.exe
    for size in (16, 32, 48):
        images[f"img/ie-{size}.png"] = assets.icon("ie-page", size)
    zen = os.path.join(ROOT, "src", "zen-ie")
    import io
    with zipfile.ZipFile(os.path.join(out, "zorin-xp-ie@zorin-xp.local.xpi"), "w", zipfile.ZIP_DEFLATED) as z:
        core = os.path.join(zen, "extension")
        for d, _dirs, files in sorted(os.walk(core)):
            for f in sorted(files):
                path = os.path.join(d, f)
                z.write(path, os.path.relpath(path, core))
        for name in ("sounds", "favorites", "history", "explorerbar", "find"):
            for f in sorted(os.listdir(os.path.join(zen, name))):
                z.write(os.path.join(zen, name, f), f)
        for name in ("lastdir", "tabflash", "sidebarpin", "title", "scrollbars"):
            for f in ("api.js", "schema.json"):
                z.write(os.path.join(zen, name, f), f"experiments/{name}/{f}")
        for arc, path in copies.items():
            z.write(path, arc)
        for arc, im in images.items():
            buf = io.BytesIO()
            im.save(buf, "PNG")
            z.writestr(arc, buf.getvalue())
        for name, path in oggs.items():
            z.write(path, name)
            os.remove(path)
    # (the nine extensions of earlier versions: install.sh takes them out of the profile)
    for old in OLD_EXTENSIONS:
        stale = os.path.join(out, f"{old}.xpi")
        if os.path.exists(stale):
            os.remove(stale)


def statusbar(img):
    # (pieces of an IE6 capture, 23 px high: assets/captures/ie6/ORIGEM.md)
    for name in ("status-bg", "status-sep", "status-gripper"):
        assets.capture(f"ie6/{name}").save(os.path.join(img, f"{name}.png"))
    # empty progress bar (the block columns covered with one from the middle)
    bar = assets.capture("ie6/progress")
    mid = bar.crop((50, 0, 51, bar.height))
    for x in range(4, 40):
        bar.paste(mid, (x, 0))
    bar.save(os.path.join(img, "progress.png"))
    # address box drop-down button (15x18, inside the border)
    assets.capture("ie6/combo-drop").save(os.path.join(img, "combo-drop.png"))
    # strip of 11 green blocks (each: block + gap, 8 px), only the block rows
    # (y 917..927): it comes in from the left block by block

    chunk = assets.capture("ie6/progress-chunk")
    strip = Image.new("RGB", (88, chunk.height))
    for i in range(11):
        strip.paste(chunk, (i * 8, 0))
    strip.save(os.path.join(img, "progress-chunks.png"))


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1], sys.argv[2]))
