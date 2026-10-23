"""Reading the resources extracted into assets/ (tools/extract.py), by name.

This is how the build gets to XP's images, icons, cursors, sounds, fonts
and texts — never to the Windows copy.

  theme("luna")        the visual style: the same interface as msstyles.MsStyles
                       (part, states, image...), read from assets/themes/luna
  sound("Windows XP Startup.wav"), font("tahoma.ttf"), fonts_dir()
  font_named("Franklin Gothic Medium", italic=True)   the font by name
  cursor("default")    [(image, hotspot)] of the .cur, like wincursor
  icon("folder", 16)   the icon's 16 px image (assets/icons/folder.ico)
  image("ie/toolbar")  an image from the DLLs (assets/images/ie/toolbar.png)
  capture("ie6/status-bg")  a piece cropped from a real XP capture
                       (assets/captures/ie6/status-bg.png; not in any Windows file)
  raw_bitmap("boot/screen")  a bitmap as it is (the DIB, without the header)
  string("shell32", 9092), dialog("comdlg32", 1552), menu_item("shell32", 215, 28717)
                       texts of the language (assets/locales/pt-PT), by Windows id
"""
import json
import ntpath
import os

from PIL import Image

from lib import msstyles
from lib import wincursor
from lib import winicons
from lib.paths import ASSETS, DEFAULT_LOCALE

# the language of the texts (assets/locales/<language>); ZXP_LOCALE=en-US for another
LOCALE = os.environ.get("ZXP_LOCALE", DEFAULT_LOCALE)


def _find(folder, name):
    """File in an assets folder, case-insensitively."""
    low = name.lower()
    for f in os.listdir(folder):
        if f.lower() == low:
            return os.path.join(folder, f)
    raise FileNotFoundError(os.path.join(folder, name))


class Theme(msstyles.MsStyles):
    """Extracted visual style: theme.ini (the colour scheme INI) and its
    images in bitmaps/ (with the INI's name); the Explorer task pane in
    shell/. Read like an MsStyles."""

    def __init__(self, name="luna"):
        self.name = name
        self.dir = os.path.join(ASSETS, "themes", name)
        with open(os.path.join(self.dir, "theme.ini"), encoding="utf-8") as f:
            self.ini_text = f.read()
        self.parts = msstyles.parse_ini(self.ini_text)

    def bitmap(self, ini_path):
        """'Blue\\FrameCaption.bmp' (as in the INI) -> RGBA image."""
        base = ntpath.basename(ini_path)
        path = _find(os.path.join(self.dir, "bitmaps"), base[:-4] + ".png")
        return Image.open(path).convert("RGBA")

    def shell(self, name):
        """Image of the Explorer task pane (e.g. "section-header")."""
        return Image.open(os.path.join(self.dir, "shell", f"{name}.png")).convert("RGBA")


_themes = {}


def theme(name="luna"):
    if name not in _themes:
        _themes[name] = Theme(name)
    return _themes[name]


_icons = {}


def icon_images(name):
    """[(w, h, bpp, RGBA image)] of assets/icons/<name>.ico, from best to
    worst (like winicons.group_icons)."""
    if name not in _icons:
        with open(os.path.join(ASSETS, "icons", f"{name}.ico"), "rb") as f:
            _icons[name] = winicons.ico_icons(f.read())
    return _icons[name]


def icon(name, size):
    """The icon's image at that size (the deepest one), or None if XP did
    not have it (like winicons.best)."""
    cands = [e for e in icon_images(name) if e[0] == size]
    return max(cands, key=lambda e: e[2])[3].copy() if cands else None


def image(name):
    """RGBA image of assets/images/<area>/<name>.png (e.g. "ie/toolbar")."""
    return Image.open(os.path.join(ASSETS, "images", f"{name}.png")).convert("RGBA")


def capture(name):
    """RGB image of assets/captures/<name>.png: what XP draws without a file of
    its own, cropped from a real capture (see the folder's ORIGEM.md)."""
    return Image.open(os.path.join(ASSETS, "captures", f"{name}.png")).convert("RGB")


def raw_bitmap(name):
    """The DIB as it is from assets/images/<area>/<name>.bmp (without the
    file header), as it came in the resource."""
    with open(os.path.join(ASSETS, "images", f"{name}.bmp"), "rb") as f:
        return f.read()[14:]


def sounds_dir():
    return os.path.join(ASSETS, "sounds")


def sound(name):
    return _find(sounds_dir(), name)


def fonts_dir():
    return os.path.join(ASSETS, "fonts")


def font(name):
    return _find(fonts_dir(), name)


_font_names = {}


def font_named(family, bold=False, italic=False):
    """The font file with that family name and style (as themes ask for
    them: "Franklin Gothic Medium" italic -> framdit.ttf)."""
    if not _font_names:
        from PIL import ImageFont
        for f in sorted(os.listdir(fonts_dir())):
            if f.lower().endswith((".ttf", ".otf")):
                fam, style = ImageFont.truetype(os.path.join(fonts_dir(), f), 12).getname()
                st = style.lower()
                _font_names[fam.lower(), "bold" in st, "italic" in st or "oblique" in st] = f
    return os.path.join(fonts_dir(), _font_names[family.lower(), bold, italic])


def cursor(name):
    """[(RGBA image, (x, y) of the hotspot)] of assets/cursors/<name>.cur."""
    with open(os.path.join(ASSETS, "cursors", f"{name}.cur"), "rb") as f:
        return wincursor.read_cur(f.read())


# --------------------------------------------------------------------------
# Texts of the language (assets/locales/<language>/<file>.json), by id
# --------------------------------------------------------------------------
_texts = {}


def _texts_of(source):
    """{"strings", "dialogs", "menus"} of a Windows file ("shell32" or
    "shell32.dll"), with numeric ids."""
    base = source.rsplit(".", 1)[0].lower() if source.lower().endswith((".dll", ".exe")) else source.lower()
    if base not in _texts:
        with open(os.path.join(ASSETS, "locales", LOCALE, f"{base}.json"), encoding="utf-8") as f:
            data = json.load(f)
        _texts[base] = {k: {int(i): v for i, v in data[k].items()} for k in ("strings", "dialogs", "menus")}
    return _texts[base]


def string(source, sid):
    """A text (string table) by id; "" if it does not exist."""
    return _texts_of(source)["strings"].get(sid, "")


def dialog(source, did):
    """A dialog template (like dlgtemplate.dialog: title, font, size in
    DLU and the controls with id, class, text and position)."""
    return _texts_of(source)["dialogs"][did]


def dialog_texts(source, did, mnemonics=False):
    """{control id: text} of a dialog; without the "&" of the mnemonics,
    unless mnemonics=True."""
    return {c["id"]: str(c["text"]) if mnemonics else str(c["text"]).replace("&", "")
            for c in dialog(source, did)["controls"]}


def menu(source, mid):
    """The items of a menu (winmenus.parse: id, text, submenus)."""
    return _texts_of(source)["menus"][mid]


def menu_item(source, mid, item_id=None):
    """The text (with the "&") of a menu item by command id; without an id,
    the first item with text."""
    from lib import winmenus
    for item in winmenus.flat(menu(source, mid)):
        if item["text"] and (item_id is None or item["id"] == item_id):
            return item["text"]
    raise KeyError(f"{source} menu {mid}: item {item_id}")


def registry_text(key):
    """A text that comes from the registry in XP (catalog.REGISTRY_TEXTS)."""
    with open(os.path.join(ASSETS, "locales", LOCALE, "registry.json"), encoding="utf-8") as f:
        return json.load(f)[key]


def locale_file(path):
    """A file of the language (e.g. "ie/dnserror.htm"), in bytes."""
    with open(os.path.join(ASSETS, "locales", LOCALE, path), "rb") as f:
        return f.read()


def image_file(path):
    """A named image stored as it is (e.g. "ie/pagerror.gif"), in bytes."""
    with open(os.path.join(ASSETS, "images", path), "rb") as f:
        return f.read()
