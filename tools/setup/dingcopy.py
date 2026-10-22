#!/usr/bin/env python3
"""Cópia do programa dos ícones do ambiente de trabalho (zorin-desktop-icons)
com a grelha do XP.

A grelha está fixa no código da extensão do Zorin (enums.js: largura e altura
de cada célula para cada tamanho de ícone), que fica em /usr/share e não se
mexe. Copia-se a pasta app/ para <saída>/app e muda-se só o tamanho "small"
(ícones de 48 px): o XP põe os ícones de 32 px a cada 78 px na vertical e
na horizontal (medido na captura de referência; 75 px de espaçamento +
margens); com 48 px fica 78 + 16 = 94 px. A célula final é a altura do ecrã
dividida pelo número de linhas que cabem com ICON_HEIGHT + 8 px.

Na mesma cópia, a seleção como no XP (desktopIconItem.js): o ícone
selecionado fica misturado com a cor de realce (ImageList ILD_BLEND50, a mesma
conta da extensão do Ficheiros, src/nautilus-xp: _blend); se o código do
Zorin mudar, fica só a grelha.

Ainda na cópia, o resto do ambiente de trabalho do XP (src/desktop/zxpDesktop.js,
ligado em desktopManager.js): o nome editado no sítio (Nova pasta, F2, Mudar o
nome), a pergunta do XP ao eliminar com o som da Reciclagem e o menu do fundo
do XP. Os textos e os ícones das caixas vêm do XP (pasta app/zxp).

desktopNames.js usa a cópia só se o stamp.json bater certo com os ficheiros
originais (tamanho e data): depois de uma atualização do Zorin volta à
original até se correr o install.sh outra vez.

Uso: dingcopy.py <pasta de saída>
"""
import json
import os
import re
import shutil
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.paths import ROOT  # noqa: E402

SRC = "/usr/share/gnome-shell/extensions/zorin-desktop-icons@zorinos.com/app"
# ganchos em desktopManager.js: (texto que tem de existir uma vez, o que se junta a seguir)
HOOKS = [
    ("    doRename(fileItem, allowReturnOnSameName) {\n",
     "        return imports.zxpDesktop.startRename(this, fileItem, allowReturnOnSameName);\n"),
    ("    doTrash() {\n", "        return imports.zxpDesktop.confirmDelete(this, false);\n"),
    ("    doDeletePermanently() {\n", "        return imports.zxpDesktop.confirmDelete(this, true);\n"),
    ("    _prepareMenu() {\n", "        imports.zxpDesktop.prepareMenu(this);\n"),
    ("        this._menu.show_all();\n    }\n\n    _selectAll() {",
     None),
]
CELL = 86          # + 8 px de espaçamento da grelha -> ~94/95 px por célula

SET_ICON = re.compile(r"let surface = Gdk\.cairo_surface_create_from_pixbuf\(pixbuf, scale, null\);\n"
                      r"\s*this\._icon\.set_from_surface\(surface\);")
SELECTED = "    _setSelectedStatus() {\n"
BEFORE = "    _getDefaultIcon() {\n"
METHODS = """    // Zorin XP: o ícone guardado, para o mostrar misturado quando selecionado
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
/* Zorin XP: a seleção do XP (ImageList ILD_BLEND50, medida numa captura do
   XP): os píxeis com alfa >= 128 a meio caminho da cor de realce #316AC5, no
   alfa pré-multiplicado; os outros (sombras) ficam iguais */
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


def patch_desktop(app):
    """O módulo do XP e os ganchos no desktopManager.js (tudo ou nada)."""
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
    # (os mesmos textos e ícones da janela de ficheiros: tools/builders/filechooser.py)
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
    patch_desktop(app)
    with open(os.path.join(out, "stamp.json"), "w") as f:
        json.dump({"src": src, "files": stamp(src)}, f, indent=1)
    return True


if __name__ == "__main__":
    sys.exit(0 if build(sys.argv[1]) else 1)
