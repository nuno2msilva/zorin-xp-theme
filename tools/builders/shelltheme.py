"""GNOME Shell theme: taskbar, Start button and Zorin menu, XP style.

Starts from the Zorin Shell theme installed on the system (so the rest of
the Shell stays consistent with Zorin's extensions) and adds
src/shell/xp.css to it, with the elements pre-drawn from luna.msstyles at
the measurements checked against real XP captures.
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
START_LABEL_ID = 578            # explorer.exe: the Start button label


def _m(ms, part):
    v = ms.part(part).ints("SizingMargins") or [0, 0, 0, 0]
    return tuple(v)


def start_button(ms, out):
    """The 3 states of the Start button (normal, hover, pressed), with the
    language's text drawn the way XP draws it. Returns the width.

    The button is a comctl32 Button with the theme's "Start::Button" class:
    the flag (explorer.exe, bitmap 143) and the text (string 578: "Iniciar",
    "start" in English XP) inside the ContentMargins, the text with the
    theme's font, colour and "continuous" shadow (lib/xpdraw). The width is
    the text's plus the margins, the flag and 2 px: "Iniciar" (51 px) gives
    112, "start" (38 px) gives 99, the width of StartButton.bmp. The button
    window starts 1 px before the screen and reaches 2 px below it: it shows
    from x = 1 and its top 30 rows.
    Identical to the real captures (reference/start-button), except for 2
    pixels of the "I" (FreeType's hinting puts one point of the "I" 1/64 px
    away from XP's).
    """
    part = ms.part("Start::Button")
    label = assets.string("explorer", START_LABEL_ID)
    font = xpdraw.theme_font(part.get("Font"), assets.font_named)
    left, right, top, bottom = part.ints("ContentMargins")
    flag = assets.image("taskbar/start-flag")
    win_w, win_h = font.extent(label) + left + right + flag.width + 2, TASKBAR_H + 2
    width = win_w - 1
    # (on screen: everything 1 px left of where it is in the window)
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
    # Background (TaskBar.BackgroundBottom): wide enough for any screen
    bgm = _m(ms, "TaskBar.BackgroundBottom")
    strip = uxrender.render(ms.states("TaskBar.BackgroundBottom")[0], 50, TASKBAR_H, bgm, tile=True)
    wide = Image.new("RGBA", (7680, TASKBAR_H))
    for x in range(0, wide.width, strip.width):
        wide.paste(strip, (x, 0))
    wide.save(os.path.join(out, "taskbar-bg.png"))
    # 160×30 window buttons: 0 normal, 1 hover, 2/4 active, 3/5 active + hover
    tb = ms.states("TaskBand::Toolbar.Button")
    tm = _m(ms, "TaskBand::Toolbar.Button")
    for idx, name in ((0, "normal"), (1, "hover"), (4, "active"), (5, "active-hover"), (2, "pressed")):
        uxrender.render(tb[idx], TASKBAND_W, TASKBAR_H, tm).save(os.path.join(out, f"taskband-{name}.png"))
    # Notification area, already at the bar's height (it only stretches horizontally)
    tray = ms.states("TrayNotifyHoriz::TrayNotify.Background")[0]
    uxrender.render(tray, 300, TASKBAR_H, _m(ms, "TrayNotifyHoriz::TrayNotify.Background")).save(
        os.path.join(out, "tray.png"))
    # "Show hidden icons" arrow (19×20, real size): closed "<" and open ">",
    # each one normal / hover / pressed
    for part, kind in (("TrayNotifyHoriz::Button", "closed"), ("TrayNotifyHorizOpen::Button", "open")):
        for state, img in zip(("normal", "hover", "active"), ms.states(part)):
            img.save(os.path.join(out, f"tray-chevron-{kind}-{state}.png"))


# Start menu widths (XP uses 380 = 190 + 190); the pieces are drawn by
# uxrender at this width. startmenu.js uses the same values.
START_W, LEFT_W = 380, 190
HEADER_H, FOOTER_H = 64, 41    # UserPane 64; Logoff medido em captura real: 41


def startmenu_xp(ms, out):
    """XP Start menu pieces pre-drawn at XP's sizes."""
    def r(part, w, h, i=0, tile=False):
        return uxrender.render(ms.states(part)[i], w, h, _m(ms, part), tile=tile)
    r("StartPanel.UserPane", START_W, HEADER_H).save(os.path.join(out, "start-header.png"))
    r("StartPanel.Logoff", START_W, FOOTER_H).save(os.path.join(out, "start-footer.png"))
    # Column backgrounds (they include the orange line, the side borders and the divider)
    r("StartPanel.ProgList", LEFT_W, 1200).save(os.path.join(out, "start-left.png"))
    r("StartPanel.PlacesList", START_W - LEFT_W, 1200).save(os.path.join(out, "start-right.png"))
    r("StartPanel.MorePrograms", LEFT_W, 30).save(os.path.join(out, "start-more-bg.png"))
    ms.states("StartPanel.MoreProgramsArrow")[0].save(os.path.join(out, "start-more-arrow.png"))
    ms.states("StartPanel.MoreProgramsArrow(hot)")[0].save(os.path.join(out, "start-more-arrow-hot.png"))
    # "Voltar" (Back; does not exist in XP): the same arrow, mirrored
    for part, suffix in (("StartPanel.MoreProgramsArrow", ""), ("StartPanel.MoreProgramsArrow(hot)", "-hot")):
        ms.states(part)[0].transpose(Image.FLIP_LEFT_RIGHT).save(
            os.path.join(out, f"start-back-arrow{suffix}.png"))
    # Frame of the user's picture (UserTileBackground), 48 px + content margins
    tile = ms.part("StartPanel.UserPicture")
    cl, cr, ct, cb = tile.ints("ContentMargins")
    r("StartPanel.UserPicture", 48 + cl + cr, 48 + ct + cb).save(os.path.join(out, "start-usertile.png"))
    # Session icons (24×24): 0 eject, 1 log off, 2 turn off
    for part, suffix in (("StartPanel.LogoffButtons", ""), ("StartPanel.LogoffButtons(hot)", "-hot")):
        strip = ms.states(part)[0]
        for k, name in ((1, "logoff"), (2, "shutdown")):
            strip.crop((k * 24, 0, k * 24 + 24, 24)).save(os.path.join(out, f"start-{name}{suffix}.png"))
    # Right column icons (XP's native 24 px, as in the real Start menu:
    # My Documents 235, pictures 236, music 237, My Computer 16,
    # Control Panel 22 — identified to the pixel in an XP capture)
    # (without 24 px in XP: the biggest one scaled down, as in the icon theme)
    from builders import icons
    for key, name in {
        "computer": "computer", "desktop": "desktop",
        "documents": "folder-documents", "music": "folder-music",
        "pictures": "folder-pictures", "videos": "folder-videos",
        "programs": "add-remove-programs", "settings": "control-panel",
        "appearance": "appearance-and-themes", "terminal": "cmd",
        "internet": "internet", "help": "help-and-support",
        # Downloads (XP did not have it): the same icon as the icon theme's folder
        "downloads": "composite:downloads",
    }.items():
        icons.image(name, 24).save(os.path.join(out, f"start-ico-{key}.png"))
    for part, name in (("StartPanel.ProgListSeparator", "start-sep-left"),
                       ("StartPanel.PlacesListSeparator", "start-sep-right")):
        ms.states(part)[0].save(os.path.join(out, f"{name}.png"))
    start_shadow().save(os.path.join(out, "start-shadow.png"))


# Start menu shadow (CS_DROPSHADOW). It is not in the theme: win32k draws
# it. Measured in a real capture (Screenshot_20261011172149): 5 px to the
# right and below, black with these opacities by distance to the edge; the
# bottom corner uses the bigger of the two distances; at the top right
# (rounded corner) and at the bottom left the shadow fades in as below.
SHADOW_ALPHA = (0.44, 0.33, 0.17, 0.055, 0.01)
SHADOW_TOP_RIGHT = (   # distance per row (counting from the top of the menu) and column; 0 = no shadow
    (5, 5, 0, 0, 0), (4, 5, 5, 0, 0), (4, 4, 5, 5, 0), (3, 4, 4, 5, 0),
    (3, 3, 4, 5, 5), (2, 3, 4, 4, 5), (2, 3, 3, 4, 5), (2, 2, 3, 4, 5),
)
SHADOW_TOP, SHADOW_LEFT = 6, 10   # rows without shadow at the top; columns of the fade on the left


def start_shadow():
    """9-slice image (border-image 15 5 5 10) for an 11×16 menu."""
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
        start = max(1, SHADOW_LEFT - x)    # x=9 full, x=8 from 2, ...
        for r in range(n):
            put(x, mh + r, max(start, r + 1) if start <= n else 0)
    return img


SCROLL_W = 17   # SM_CXVSCROLL do XP


def scrollbar_assets(ms, out):
    """XP vertical scrollbar for St (StScrollBar).

    St has no arrow buttons: the bar gets 17 px of padding at the top and
    bottom and a border-image (17 0 17 0) with the arrows and the trough;
    startmenu.js handles the clicks and swaps the image when an arrow is
    highlighted/pressed.
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


# XP's notification area icons (16 px), for the system indicators:
# systray volume (stobject.dll), microphone (the handheld one with a balloon
# from the Speech panel, sapi.cpl — only in dllcache), location (XP did not
# have it: the globe of Regional Options, intl.cpl), network — in XP the
# wireless network uses the same two-monitor icon (netshell.dll) —, Bluetooth
# (irprops.cpl) and the battery strip of the power meter (batmeter.dll, 10
# 16 px states with magenta as the colour key)
# notification area icons: tray-ico-<key>.png <- assets/icons
TRAY_ICONS = {
    "volume": "tray-volume", "volume-muted": "tray-volume-muted",
    "mic": "tray-mic",
    "location": "regional-options",
    # two monitors: off, the front one lit sending, the back one receiving,
    # both — how XP showed the activity
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
    """Menu frame: blue top cap (StartUserPanel), bottom cap
    (StartPanelLogoff), separators and the backgrounds of both columns."""
    startmenu_xp(ms, out)
    W = 64
    top = uxrender.render(ms.states("StartPanel.UserPane")[0], W, 64, _m(ms, "StartPanel.UserPane"))
    bottom = uxrender.render(ms.states("StartPanel.Logoff")[0], W, 40, _m(ms, "StartPanel.Logoff"))
    frame = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    frame.alpha_composite(top.crop((0, 0, W, 8)), (0, 0))
    frame.alpha_composite(bottom.crop((0, 40 - 8, W, 40)), (0, W - 8))
    # sides: the outer columns of the top cap (rows below the corners)
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
