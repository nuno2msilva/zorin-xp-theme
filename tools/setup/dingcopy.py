#!/usr/bin/env python3
"""Copy of the desktop icons program (zorin-desktop-icons) with XP's grid.

The grid is fixed in the Zorin extension's code (enums.js: width and height
of each cell for each icon size), which lives in /usr/share and is not
touched. The app/ folder is copied to <out>/app and only the "small" size
(48 px icons) is changed: XP puts its 32 px icons every 78 px vertically and
horizontally (measured in the reference capture; 75 px of spacing +
margins); with 48 px that is 78 + 16 = 94 px. The final cell is the screen
height divided by the number of rows that fit with ICON_HEIGHT + 8 px.

In the same copy, XP's selection (desktopIconItem.js): the selected icon is
blended with the highlight colour (ImageList ILD_BLEND50, the same maths as
the Files extension, src/nautilus-xp: _blend); if Zorin's code changes, only
the grid stays. The trash icon is named by our translation ("Reciclagem")
instead of gvfs's name (fileItem.js).

Also in the copy, the rest of XP's desktop (src/desktop/zxpDesktop.js, hooked
into desktopManager.js): the name edited in place (New folder, F2, Rename),
XP's question when deleting with the Recycle Bin sound and XP's background
menu. The texts and the boxes' icons come from XP (the app/zxp folder).

desktopNames.js only uses the copy if stamp.json matches the original files
(size and date): after a Zorin update it goes back to the original until
install.sh is run again.

Usage: dingcopy.py <output folder>
"""
import json
import os
import re
import shutil
import sys

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.paths import ROOT  # noqa: E402

SRC = "/usr/share/gnome-shell/extensions/zorin-desktop-icons@zorinos.com/app"
# hooks in desktopManager.js: (text that must exist exactly once, what is added after it)
HOOKS = [
    ("    doRename(fileItem, allowReturnOnSameName) {\n",
     "        return imports.zxpDesktop.startRename(this, fileItem, allowReturnOnSameName);\n"),
    ("    doTrash() {\n", "        return imports.zxpDesktop.confirmDelete(this, false);\n"),
    ("    doDeletePermanently() {\n", "        return imports.zxpDesktop.confirmDelete(this, true);\n"),
    ("    _prepareMenu() {\n", "        imports.zxpDesktop.prepareMenu(this);\n"),
    ("        this._menu.show_all();\n    }\n\n    _selectAll() {",
     None),
]
CELL = 86          # + 8 px of grid spacing -> ~94/95 px per cell

SET_ICON = re.compile(r"let surface = Gdk\.cairo_surface_create_from_pixbuf\(pixbuf, scale, null\);\n"
                      r"\s*this\._icon\.set_from_surface\(surface\);")
SELECTED = "    _setSelectedStatus() {\n"
BEFORE = "    _getDefaultIcon() {\n"
METHODS = """    // Zorin XP: the stored icon, to show it blended when selected
    _zxpSetIcon(pixbuf, scale) {
        this._zxpPixbuf = pixbuf;
        this._zxpScale = scale;
        this._zxpBlended = null;
        this._zxpShowIcon();
    }

    _zxpShowIcon() {
        if (!this._zxpPixbuf || !this._icon)
            return;
        let pixbuf = this._zxpPixbuf;
        if (this._isSelected) {
            if (!this._zxpBlended)
                this._zxpBlended = zxpBlend(pixbuf);
            pixbuf = this._zxpBlended;
        }
        this._icon.set_from_surface(Gdk.cairo_surface_create_from_pixbuf(pixbuf, this._zxpScale, null));
    }

"""
BLEND = """
/* Zorin XP: XP's selection (ImageList ILD_BLEND50, measured in an XP
   capture): pixels with alpha >= 128 halfway to the highlight colour #316AC5,
   in premultiplied alpha; the others (shadows) stay the same */
function zxpBlend(pixbuf) {
    if (!pixbuf.get_has_alpha())
        pixbuf = pixbuf.add_alpha(false, 0, 0, 0);
    const w = pixbuf.get_width(), h = pixbuf.get_height();
    const stride = pixbuf.get_rowstride(), n = pixbuf.get_n_channels();
    const src = pixbuf.read_pixel_bytes().toArray();
    const out = new Uint8Array(src);
    const hl = [0x31, 0x6A, 0xC5];
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const i = y * stride + x * n;
            const a = src[i + 3];
            if (a < 128)
                continue;
            for (let c = 0; c < 3; c++) {
                const p = Math.round(src[i + c] * a / 255);
                out[i + c] = Math.min(255, Math.round(((p + hl[c] + 1) >> 1) * 255 / a));
            }
        }
    }
    return GdkPixbuf.Pixbuf.new_from_bytes(new GLib.Bytes(out), GdkPixbuf.Colorspace.RGB,
        true, 8, w, h, stride);
}
"""


def patch_selection(path):
    text = open(path, encoding="utf-8").read()
    new, n = SET_ICON.subn("this._zxpSetIcon(pixbuf, scale);", text)
    if n != 3 or new.count(SELECTED) != 1 or new.count(BEFORE) != 1:
        print("  desktopIconItem.js do zorin-desktop-icons mudou: seleção do XP não aplicada",
              file=sys.stderr)
        return False
    new = new.replace(SELECTED, SELECTED + "        this._zxpShowIcon();\n")
    new = new.replace(BEFORE, METHODS + BEFORE) + BLEND
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


TRASH_ANCHOR = "    _getVisibleName() {\n"
TRASH_NAME = ("        // Zorin XP: the trash is named by our translation (\"Reciclagem\",\n"
              "        // tools/setup/molocale.py), not by gvfs (\"Lixo\")\n"
              "        if (this._fileExtra == Enums.FileType.USER_DIRECTORY_TRASH)\n"
              "            return _('Trash');\n")


def patch_trash_name(path):
    """The desktop trash icon gets its label from gvfs's display name of
    trash:///, which our translations do not reach: use the program's own
    _('Trash') instead, like the screen-reader name next to it."""
    text = open(path, encoding="utf-8").read()
    if text.count(TRASH_ANCHOR) != 1:
        print("  fileItem.js of zorin-desktop-icons changed: XP trash name not applied", file=sys.stderr)
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(TRASH_ANCHOR, TRASH_ANCHOR + TRASH_NAME))
    return True


def patch_desktop(app):
    """XP's module and the hooks in desktopManager.js (all or nothing)."""
    path = os.path.join(app, "desktopManager.js")
    text = open(path, encoding="utf-8").read()
    new = text
    for anchor, add in HOOKS:
        if new.count(anchor) != 1:
            print("  desktopManager.js do zorin-desktop-icons mudou: ambiente de trabalho do XP não aplicado",
                  file=sys.stderr)
            return False
        if add is None:         # (o menu do XP no fim do menu do Zorin)
            new = new.replace(anchor, anchor.replace("        this._menu.show_all();\n",
                                                     "        this._menu.show_all();\n"
                                                     "        imports.zxpDesktop.xpMenu(this);\n"))
        else:
            new = new.replace(anchor, anchor + add)
    data = os.path.join(app, "zxp")
    os.makedirs(data, exist_ok=True)
    module = open(os.path.join(ROOT, "src", "desktop", "zxpDesktop.js"), encoding="utf-8").read()
    with open(os.path.join(app, "zxpDesktop.js"), "w", encoding="utf-8") as f:
        f.write(module.replace("'@DATA@'", json.dumps(data)))
    # (the same texts and icons as the file dialog: tools/builders/filechooser.py)
    from builders import filechooser
    with open(os.path.join(data, "strings.json"), "w", encoding="utf-8") as f:
        json.dump(filechooser.xp_strings(), f, ensure_ascii=False, indent=1)
    filechooser.export_msg_icons(data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


def stamp(src):
    out = {}
    for name in sorted(os.listdir(src)):
        st = os.stat(os.path.join(src, name))
        out[name] = [st.st_size, int(st.st_mtime)]
    return out


def build(out, src=SRC):
    if not os.path.isdir(src):
        return False
    app = os.path.join(out, "app")
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(src, app)
    enums = os.path.join(app, "enums.js")
    text = open(enums, encoding="utf-8").read()
    new = text
    for key in ("ICON_WIDTH", "ICON_HEIGHT"):
        new = re.sub(rf"(var {key} = \{{[^}}]*'small': )\d+", rf"\g<1>{CELL}", new)
    if new.count(f"'small': {CELL}") != 2:
        shutil.rmtree(out, ignore_errors=True)
        print("  enums.js do zorin-desktop-icons mudou: grelha do XP não aplicada", file=sys.stderr)
        return False
    with open(enums, "w", encoding="utf-8") as f:
        f.write(new)
    patch_selection(os.path.join(app, "desktopIconItem.js"))
    patch_trash_name(os.path.join(app, "fileItem.js"))
    patch_desktop(app)
    with open(os.path.join(out, "stamp.json"), "w") as f:
        json.dump({"src": src, "files": stamp(src)}, f, indent=1)
    return True


if __name__ == "__main__":
    sys.exit(0 if build(sys.argv[1]) else 1)
