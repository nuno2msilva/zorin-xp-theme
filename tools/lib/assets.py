"""Leitura dos recursos extraídos para assets/ (tools/extract.py), por nome.

É por aqui que a construção chega às imagens, ícones, cursores, sons, letras
e textos do XP — nunca à cópia do Windows.

  theme("luna")        o tema visual: a mesma interface que msstyles.MsStyles
                       (part, states, image...), lida de assets/themes/luna
  sound("Windows XP Startup.wav"), font("tahoma.ttf"), fonts_dir()
  font_named("Franklin Gothic Medium", italic=True)   a letra pelo nome
  cursor("default")    [(imagem, ponto ativo)] do .cur, como wincursor
  icon("folder", 16)   a imagem de 16 px do ícone (assets/icons/folder.ico)
  image("ie/toolbar")  uma imagem das DLL (assets/images/ie/toolbar.png)
  raw_bitmap("boot/screen")  um bitmap tal e qual (o DIB, sem cabeçalho)
  string("shell32", 9092), dialog("comdlg32", 1552), menu_item("shell32", 215, 28717)
                       textos da língua (assets/locales/pt-PT), pelo id do Windows
"""
import json
import ntpath
import os

from PIL import Image

from lib import msstyles
from lib import wincursor
from lib import winicons
from lib.paths import ASSETS, DEFAULT_LOCALE

# a língua dos textos (assets/locales/<língua>); ZXP_LOCALE=en-US para outra
LOCALE = os.environ.get("ZXP_LOCALE", DEFAULT_LOCALE)


def _find(folder, name):
    """Ficheiro numa pasta de assets, sem olhar a maiúsculas."""
    low = name.lower()
    for f in os.listdir(folder):
        if f.lower() == low:
            return os.path.join(folder, f)
    raise FileNotFoundError(os.path.join(folder, name))


class Theme(msstyles.MsStyles):
    """Tema visual extraído: theme.ini (o INI do esquema de cores) e as suas
    imagens em bitmaps/ (com o nome do INI); o painel de tarefas do
    Explorador em shell/. Lê-se como um MsStyles."""

    def __init__(self, name="luna"):
        self.name = name
        self.dir = os.path.join(ASSETS, "themes", name)
        with open(os.path.join(self.dir, "theme.ini"), encoding="utf-8") as f:
            self.ini_text = f.read()
        self.parts = msstyles.parse_ini(self.ini_text)

    def bitmap(self, ini_path):
        """'Blue\\FrameCaption.bmp' (como no INI) -> imagem RGBA."""
        base = ntpath.basename(ini_path)
        path = _find(os.path.join(self.dir, "bitmaps"), base[:-4] + ".png")
        return Image.open(path).convert("RGBA")

    def shell(self, name):
        """Imagem do painel de tarefas do Explorador (ex.: "section-header")."""
        return Image.open(os.path.join(self.dir, "shell", f"{name}.png")).convert("RGBA")


_themes = {}


def theme(name="luna"):
    if name not in _themes:
        _themes[name] = Theme(name)
    return _themes[name]


_icons = {}


def icon_images(name):
    """[(w, h, bpp, imagem RGBA)] de assets/icons/<nome>.ico, da melhor para a
    pior (como winicons.group_icons)."""
    if name not in _icons:
        with open(os.path.join(ASSETS, "icons", f"{name}.ico"), "rb") as f:
            _icons[name] = winicons.ico_icons(f.read())
    return _icons[name]


def icon(name, size):
    """A imagem de um ícone nesse tamanho (a de maior profundidade), ou None
    se o XP não a tinha (como winicons.best)."""
    cands = [e for e in icon_images(name) if e[0] == size]
    return max(cands, key=lambda e: e[2])[3].copy() if cands else None


def image(name):
    """Imagem RGBA de assets/images/<área>/<nome>.png (ex.: "ie/toolbar")."""
    return Image.open(os.path.join(ASSETS, "images", f"{name}.png")).convert("RGBA")


def raw_bitmap(name):
    """O DIB tal e qual de assets/images/<área>/<nome>.bmp (sem o cabeçalho
    de ficheiro), como vinha no recurso."""
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
    """O ficheiro da letra com esse nome de família e estilo (como os temas a
    pedem: "Franklin Gothic Medium" itálico -> framdit.ttf)."""
    if not _font_names:
        from PIL import ImageFont
        for f in sorted(os.listdir(fonts_dir())):
            if f.lower().endswith((".ttf", ".otf")):
                fam, style = ImageFont.truetype(os.path.join(fonts_dir(), f), 12).getname()
                st = style.lower()
                _font_names[fam.lower(), "bold" in st, "italic" in st or "oblique" in st] = f
    return os.path.join(fonts_dir(), _font_names[family.lower(), bold, italic])


def cursor(name):
    """[(imagem RGBA, (x, y) do ponto ativo)] de assets/cursors/<nome>.cur."""
    with open(os.path.join(ASSETS, "cursors", f"{name}.cur"), "rb") as f:
        return wincursor.read_cur(f.read())


# --------------------------------------------------------------------------
# Textos da língua (assets/locales/<língua>/<ficheiro>.json), pelo id
# --------------------------------------------------------------------------
_texts = {}


def _texts_of(source):
    """{"strings", "dialogs", "menus"} de um ficheiro do Windows ("shell32" ou
    "shell32.dll"), com os ids em número."""
    base = source.rsplit(".", 1)[0].lower() if source.lower().endswith((".dll", ".exe")) else source.lower()
    if base not in _texts:
        with open(os.path.join(ASSETS, "locales", LOCALE, f"{base}.json"), encoding="utf-8") as f:
            data = json.load(f)
        _texts[base] = {k: {int(i): v for i, v in data[k].items()} for k in ("strings", "dialogs", "menus")}
    return _texts[base]


def string(source, sid):
    """Um texto (string table) pelo id; "" se não existir."""
    return _texts_of(source)["strings"].get(sid, "")


def dialog(source, did):
    """Um modelo de diálogo (como dlgtemplate.dialog: título, letra, tamanho
    em DLU e os controlos com id, classe, texto e posição)."""
    return _texts_of(source)["dialogs"][did]


def dialog_texts(source, did, mnemonics=False):
    """{id do controlo: texto} de um diálogo; sem o "&" das letras de atalho,
    a não ser com mnemonics=True."""
    return {c["id"]: str(c["text"]) if mnemonics else str(c["text"]).replace("&", "")
            for c in dialog(source, did)["controls"]}


def menu(source, mid):
    """Os itens de um menu (winmenus.parse: id, texto, submenus)."""
    return _texts_of(source)["menus"][mid]


def menu_item(source, mid, item_id=None):
    """O texto (com o "&") de um item do menu pelo id do comando; sem id, o
    primeiro item com texto."""
    from lib import winmenus
    for item in winmenus.flat(menu(source, mid)):
        if item["text"] and (item_id is None or item["id"] == item_id):
            return item["text"]
    raise KeyError(f"{source} menu {mid}: item {item_id}")


def registry_text(key):
    """Um texto que no XP vem do registo (catalog.REGISTRY_TEXTS)."""
    with open(os.path.join(ASSETS, "locales", LOCALE, "registry.json"), encoding="utf-8") as f:
        return json.load(f)[key]


def locale_file(path):
    """Um ficheiro da língua (ex.: "ie/dnserror.htm"), em bytes."""
    with open(os.path.join(ASSETS, "locales", LOCALE, path), "rb") as f:
        return f.read()


def image_file(path):
    """Uma imagem com nome guardada tal e qual (ex.: "ie/pagerror.gif"), em bytes."""
    with open(os.path.join(ASSETS, "images", path), "rb") as f:
        return f.read()
