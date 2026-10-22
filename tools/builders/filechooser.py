"""Dados da janela "Abrir"/"Guardar como" do XP (src/filechooser).

Do comdlg32: o modelo de diálogo 1552 (a versão com a barra de locais) e os
textos; do shell32: os nomes dos locais, das colunas, os menus do botão
direito, as caixas de eliminar/mudar o nome e a "Procurar pasta"; as imagens
da barra de ferramentas (16 px). Tudo de assets/ (ids do Windows, os mesmos
em todas as línguas: o texto vem da língua de assets/locales).

build(out) -> out/zorin-xp-filechooser/{zorin-xp-filechooser, data/...}
"""
import json
import os
import shutil

from PIL import ImageEnhance

from lib import dlgtemplate
from lib import assets
from lib.paths import ROOT

TEMPLATE = 1552        # comdlg32: Abrir/Guardar como com a barra de locais
BROWSE = 1087          # shell32: "Procurar pasta" (SHBrowseForFolder)
# posição dos botões na tira file-dialog/toolbar: voltar, um nível acima,
# nova pasta, menu "Ver"
TOOLBAR = {"back": 0, "up": 28, "newfolder": 31, "views": 32}

COMDLG = {"fileExists": 256, "replace": 257, "saveIn": 368, "saveButton": 369,
          "openButton": 370, "openTitle": 384, "saveTitle": 385, "notFound": 391,
          "pathNotFound": 392, "invalidName": 393, "saveAsType": 412,
          "upOneLevel": 702, "newFolderTip": 703, "viewList": 704, "viewDetails": 705,
          "viewMenu": 711, "back": 712}
SHELL32 = {"recent": 12691, "desktop": 9092, "documents": 9100, "computer": 9216,
           "network": 9217, "newFolder": 30320, "colName": 8976, "colSize": 8978,
           "colType": 8979, "colModified": 8980, "kb": 62, "localDisk": 9402,
           "pictures": 9076,
           # eliminar (diálogos 1011-1013 do shell32) e mudar o nome
           "askFile": 16722, "askFolder": 16723, "allContents": 66,
           "askExtension": 4112, "badChars": 4109, "renameError": 5892,
           "renameFailed": 6020, "nameExists": 6327,
           # menu do botão direito: "Novo" > "Pasta"
           "new": 30315, "newFolderItem": 30317}
# user32: os botões das caixas de mensagem
USER32 = {"yes": 805, "no": 806, "ok": 800}
# menus do shell32: (menu, id do comando) de cada texto (None: o 1.º item)
MENUS = {
    # menu "Ver" do fundo da pasta (215)
    "view": (215, 28674), "thumbnails": (215, 28717), "tiles": (215, 28718),
    "icons": (215, 28713), "list": (215, 28715), "details": (215, 28716),
    "arrange": (215, 28673), "groups": (215, 30209), "autoArrange": (215, 28753),
    "alignGrid": (215, 28756), "refresh": (215, 28931),
    "paste": (215, 28698), "pasteLink": (215, 28700), "undo": (215, 28699),
    # menus dos itens: Seleccionar (260), Abrir (305), Eliminar e Mudar o nome
    # (210), Propriedades (211), Propriedades do ambiente de trabalho (220)
    "select": (260, None), "open": (305, 1), "delete": (210, 17), "rename": (210, 18),
    "properties": (211, 19), "desktopProperties": (220, None),
}
# ícones de 32 px das caixas (msg-<chave>.png): aviso, erro, informação,
# Reciclagem vazia/cheia, eliminar de vez (ficheiro, pasta, vários)
MSG_ICONS = {"warning": "dialog-warning", "error": "dialog-error", "info": "dialog-information",
             "bin-empty": "recycle-bin", "bin-full": "recycle-bin-full",
             "kill-file": "delete-file", "kill-folder": "delete-folder", "kill-many": "delete-many"}


def xp_strings():
    """Os textos do XP da janela de ficheiros, dos menus do botão direito,
    das caixas de eliminar/mudar o nome e da "Procurar pasta"."""
    strings = {k: assets.string("comdlg32", v) for k, v in COMDLG.items()}
    strings.update({k: assets.string("shell32", v) for k, v in SHELL32.items()})
    labels = assets.dialog_texts("comdlg32", TEMPLATE, mnemonics=True)
    strings.update({"lookIn": labels[1091], "fileName": labels[1090], "filesOfType": labels[1089],
                    "cancel": labels[2]})
    strings.update({k: assets.string("user32", v) for k, v in USER32.items()})
    # tipo das pastas na vista Detalhes (no XP vem do registo: HKCR\Directory)
    strings["folderType"] = assets.registry_text("folder-type")
    strings.update({k: assets.menu_item("shell32", m, i) for k, (m, i) in MENUS.items()})
    # títulos e textos das confirmações de eliminar (ficheiro, pasta, vários)
    for key, rid in (("confirmFile", 1011), ("confirmFolder", 1012), ("confirmMany", 1013)):
        strings[key] = assets.dialog("shell32", rid)["title"]
    strings["killFile"] = assets.dialog_texts("shell32", 1011, mnemonics=True)[12295]
    strings["killFolder"] = assets.dialog_texts("shell32", 1012, mnemonics=True)[12291]
    many = assets.dialog_texts("shell32", 1013, mnemonics=True)
    strings["askMany"], strings["killMany"] = many[12291], many[12295]
    # "Procurar pasta" (com BIF_NEWDIALOGSTYLE)
    browse = assets.dialog("shell32", BROWSE)
    texts = assets.dialog_texts("shell32", BROWSE, mnemonics=True)
    strings.update({"browseTitle": browse["title"], "browseFolder": texts[14152],
                    "browseNewFolder": texts[14150], "ok": texts[1]})
    return strings


def export_msg_icons(out):
    """Os ícones de 32 px das caixas de mensagem (msg-<nome>.png)."""
    os.makedirs(out, exist_ok=True)
    for key, name in MSG_ICONS.items():
        assets.icon(name, 32).convert("RGBA").save(os.path.join(out, f"msg-{key}.png"))


def _layout(dlg):
    """Medidas de um diálogo em px (Tahoma 8 a 96 ppp): tamanho e, por id,
    [x, y, largura, altura] de cada controlo."""
    return {"size": [dlgtemplate.px(dlg["size"][0], "x"), dlgtemplate.px(dlg["size"][1], "y")],
            "controls": {str(c["id"]): [dlgtemplate.px(c["x"], "x"), dlgtemplate.px(c["y"], "y"),
                                        dlgtemplate.px(c["w"], "x"), dlgtemplate.px(c["h"], "y")]
                         for c in dlg["controls"]}}


def build(out):
    dst = os.path.join(out, "zorin-xp-filechooser")
    data = os.path.join(dst, "data")
    os.makedirs(data, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "src", "filechooser", "zorin-xp-filechooser"),
                    os.path.join(dst, "zorin-xp-filechooser"))
    os.chmod(os.path.join(dst, "zorin-xp-filechooser"), 0o755)

    with open(os.path.join(data, "strings.json"), "w", encoding="utf-8") as f:
        json.dump(xp_strings(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(data, "layout.json"), "w") as f:
        json.dump(_layout(assets.dialog("comdlg32", TEMPLATE)), f, indent=1)
    with open(os.path.join(data, "layout-browse.json"), "w") as f:
        json.dump(_layout(assets.dialog("shell32", BROWSE)), f, indent=1)

    export_msg_icons(data)
    # a pega de redimensionar do canto (Scrollbar.SizeBox do luna.msstyles: as
    # duas imagens lado a lado, 16 x 16; a primeira é a do canto direito)
    ms = assets.theme("luna")
    p = ms.part("Scrollbar.SizeBox")
    grip = ms.image(p.get("ImageFile"), True, p.color("TransparentColor", (255, 0, 0))).convert("RGBA")
    grip.crop((0, 0, grip.width // 2, grip.height)).save(os.path.join(data, "sizegrip.png"))

    # barra de ferramentas: normal, rato por cima, desativada (cinzenta como o XP)
    strips = {"normal": assets.image("file-dialog/toolbar"), "hot": assets.image("file-dialog/toolbar-hot")}
    for name, i in TOOLBAR.items():
        for st, strip in strips.items():
            strip.crop((i * 16, 0, i * 16 + 16, 16)).save(os.path.join(data, f"tb-{name}-{st}.png"))
        im = strips["normal"].crop((i * 16, 0, i * 16 + 16, 16))
        gray = ImageEnhance.Color(im).enhance(0.0)
        gray = ImageEnhance.Brightness(gray).enhance(1.25)
        gray.putalpha(im.getchannel("A").point(lambda v: v * 6 // 10))
        gray.save(os.path.join(data, f"tb-{name}-disabled.png"))
    return dst
