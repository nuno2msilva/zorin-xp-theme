"""Catálogo dos recursos do Windows XP que o tema usa: nome legível -> origem.

tools/extract.py lê este catálogo para copiar os recursos de uma cópia da
pasta Windows (windows/<cópia>) para assets/; a construção pede-os depois
pelo nome (tools/lib/assets.py), sem voltar a abrir o Windows.

Origens: "ficheiro.dll" (procurado em system32, system32/dllcache e na raiz
da cópia, sem olhar a maiúsculas) ou um caminho relativo à raiz da cópia
("Resources/Themes/Luna/luna.msstyles"). Os números são os ids dos recursos
dentro desse ficheiro (os mesmos em todas as línguas do XP).

Onde o Windows já dá um nome legível (sons, letras, imagens do tema), fica o
nome do Windows; o resto (ícones, imagens das DLL, textos) tem aqui o nome.
"""

# --------------------------------------------------------------------------
# Temas visuais (assets/themes/<nome>/): o INI do esquema de cores, tal como
# o uxtheme o lê (theme.ini), e todas as imagens que ele usa (bitmaps/, com
# o nome do INI); o painel de tarefas do Explorador (shellstyle.dll, shell/)
# e o ficheiro .theme do Windows (papel de parede, sons, cursores).
# --------------------------------------------------------------------------
THEMES = {
    "luna": {
        "title": "Luna (azul)",
        "msstyles": "Resources/Themes/Luna/luna.msstyles",
        "ini": "NORMALBLUE_INI",
        "shellstyle": "Resources/Themes/Luna/Shell/NormalColor/shellstyle.dll",
        "theme_file": "Resources/Themes/Luna.theme",
    },
}

# Imagens do painel de tarefas do Explorador (shellstyle.dll do tema): id
SHELLSTYLE = {
    # secções normais: cabeçalho (186x21, esticado) e setas recolher/abrir
    "section-header": 112,
    "section-collapse": 100,
    "section-collapse-hot": 101,
    "section-expand": 102,
    "section-expand-hot": 103,
    # secções especiais (Música, Imagens, Vídeos): cabeçalho azul e setas
    "special-header": 110,
    "special-collapse": 104,
    "special-collapse-hot": 105,
    "special-expand": 106,
    "special-expand-hot": 107,
    # ícone de 32 px, marca de água da secção e da vista de cada pasta especial
    "music-icon": 10,
    "music-section": 11,
    "music-view": 12,
    "pictures-icon": 13,
    "pictures-section": 14,
    "pictures-view": 15,
    "videos-icon": 19,
    "videos-section": 20,
    "videos-view": 21,
}

# --------------------------------------------------------------------------
# Sons (assets/sounds/): os de Windows/Media, com o nome original
# --------------------------------------------------------------------------
SOUNDS_DIR = "Media"
SOUNDS_GLOB = "*.wav"

# --------------------------------------------------------------------------
# Letras (assets/fonts/): todas as TrueType de Windows/Fonts e as de mapa de
# bits da interface. "Courier", "System", "Terminal", "Fixedsys"... ficam de
# fora: com nomes genéricos, tomariam o lugar da Courier New e outras em
# documentos, só com 3-4 tamanhos.
# --------------------------------------------------------------------------
FONTS_DIR = "Fonts"
FONT_BITMAP_FAMILIES = ("MS Sans Serif", "MS Serif", "Small Fonts")

# --------------------------------------------------------------------------
# Cursores (assets/cursors/<nome>.cur): o esquema "Predefinição do Windows",
# que vem dos recursos das DLL (não de Windows/Cursors, que são esquemas
# alternativos). Nomes = os do Xcursor/CSS.
#   user32.dll   cursores do sistema (OCR_*)
#   ole32.dll    arrastar e largar (mover / copiar / atalho / proibido)
#   comctl32.dll redimensionamento de colunas/linhas (cabeçalhos, divisórias)
#   mshtml.dll   texto vertical
# --------------------------------------------------------------------------
CURSORS = {
    "default": ("user32.dll", 100),
    "text": ("user32.dll", 101),
    "wait": ("user32.dll", 102),
    "crosshair": ("user32.dll", 103),
    "up-arrow": ("user32.dll", 104),
    "nwse-resize": ("user32.dll", 105),
    "nesw-resize": ("user32.dll", 106),
    "ew-resize": ("user32.dll", 107),
    "ns-resize": ("user32.dll", 108),
    "move": ("user32.dll", 109),
    "not-allowed": ("user32.dll", 110),
    "progress": ("user32.dll", 111),
    "help": ("user32.dll", 112),
    "pencil": ("user32.dll", 113),
    "pointer": ("user32.dll", 114),
    "all-scroll": ("user32.dll", 32654),
    "n-scroll": ("user32.dll", 32655),
    "s-scroll": ("user32.dll", 32656),
    "w-scroll": ("user32.dll", 32657),
    "e-scroll": ("user32.dll", 32658),
    "nw-scroll": ("user32.dll", 32659),
    "ne-scroll": ("user32.dll", 32660),
    "se-scroll": ("user32.dll", 32661),
    "sw-scroll": ("user32.dll", 32662),
    "ns-scroll": ("user32.dll", 32652),      # deslocamento automático só vertical
    "ew-scroll": ("user32.dll", 32653),      # ... só horizontal
    "dnd-move": ("ole32.dll", 2),
    "copy": ("ole32.dll", 3),
    "alias": ("ole32.dll", 4),
    "no-drop": ("ole32.dll", 1),
    "col-resize": ("comctl32.dll", 106),
    "row-resize": ("comctl32.dll", 135),
    "vertical-text": ("mshtml.dll", 9803),
}

# --------------------------------------------------------------------------
# Ícones (assets/icons/<nome>.ico, com todos os tamanhos e profundidades do
# grupo): (ficheiro, id do grupo de ícones; None = o primeiro, que é o ícone
# do programa). Os nomes são os do primeiro uso no tema de ícones (nomes
# freedesktop: tools/builders/icons.py); as aplicações têm o nome do programa do XP.
# --------------------------------------------------------------------------
ICONS = {
    "folder": ("shell32.dll", 4),
    "folder-open": ("shell32.dll", 5),
    "folder-documents": ("shell32.dll", 235),
    "folder-pictures": ("shell32.dll", 236),
    "folder-music": ("shell32.dll", 237),
    "folder-videos": ("shell32.dll", 238),
    "folder-publicshare": ("shell32.dll", 267),
    "folder-remote": ("shell32.dll", 10),
    "folder-saved-search": ("shell32.dll", 46),
    "folder-recent": ("shell32.dll", 21),
    "folder-new": ("shell32.dll", 319),
    "computer": ("shell32.dll", 16),
    "desktop": ("shell32.dll", 35),
    "favorites": ("shell32.dll", 44),
    "recycle-bin": ("shell32.dll", 32),
    "recycle-bin-full": ("shell32.dll", 33),
    "network-places": ("shell32.dll", 18),
    "network-server": ("netshell.dll", 1150),
    "drive-harddisk": ("shell32.dll", 9),
    "drive-removable": ("shell32.dll", 8),
    "drive-optical": ("shell32.dll", 12),
    "media-optical": ("shell32.dll", 302),
    "media-optical-cd": ("shell32.dll", 294),
    "media-optical-cd-r": ("shell32.dll", 295),
    "media-optical-cd-rw": ("shell32.dll", 296),
    "media-optical-dvd": ("shell32.dll", 304),
    "media-optical-dvd-r": ("shell32.dll", 298),
    "media-optical-dvd-rw": ("shell32.dll", 318),
    "media-optical-cd-audio": ("shell32.dll", 41),
    "media-floppy": ("shell32.dll", 7),
    "media-flash": ("shell32.dll", 308),
    "media-zip": ("shell32.dll", 312),
    "printer": ("shell32.dll", 17),
    "printer-network": ("shell32.dll", 140),
    "scanner": ("shell32.dll", 315),
    "camera-photo": ("shell32.dll", 309),
    "camera-video": ("shell32.dll", 317),
    "camera-web": ("shell32.dll", 316),
    "phone": ("shell32.dll", 310),
    "pda": ("shell32.dll", 314),
    "multimedia-player": ("shell32.dll", 306),
    "input-mouse": ("main.cpl", 100),
    "input-keyboard": ("main.cpl", 200),
    "input-gaming": ("joy.cpl", 102),
    "audio-card": ("mmsys.cpl", 4356),
    "audio-speakers": ("mmsys.cpl", 3004),
    "audio-input-microphone": ("mmsys.cpl", 4369),
    "video-display": ("setupapi.dll", 1),
    "battery": ("powercfg.cpl", 200),
    "uninterruptible-power-supply": ("powercfg.cpl", 201),
    "network-wired": ("netshell.dll", 190),
    "network-wireless": ("xpsp2res.dll", 1003),
    "modem": ("setupapi.dll", 9),
    "bluetooth": ("xpsp2res.dll", 200),
    "explorer": ("explorer.exe", None),
    "control-panel": ("shell32.dll", 22),
    "cmd": ("cmd.exe", None),
    "notepad": ("notepad.exe", None),
    "calc": ("calc.exe", None),
    "charmap": ("charmap.exe", None),
    "fonts-folder": ("fontext.dll", 1),
    "cleanmgr": ("cleanmgr.exe", None),
    "disk-management": ("dmdskres.dll", 362),
    "picture-viewer": ("shimgvw.dll", 1),
    "document": ("shell32.dll", 2),
    "compressed-folder": ("zipfldr.dll", 101),
    "eventvwr": ("eventvwr.exe", None),
    "media-player": ("wmploc.dll", 102),
    "passwords": ("shell32.dll", 194),
    "add-remove-programs": ("appwiz.cpl", 1500),
    "automatic-updates": ("wuaucpl.cpl", 1),
    "sndrec32": ("sndrec32.exe", None),
    "taskmgr": ("taskmgr.exe", None),
    "help-and-support": ("shell32.dll", 24),
    "date-time": ("timedate.cpl", 200),
    "user-accounts": ("nusrmgr.cpl", 200),
    "ntbackup": ("ntbackup.exe", None),
    "wiaacmgr": ("wiaacmgr.exe", None),
    "tourstart": ("tourstart.exe", None),
    "firewall": ("xpsp2res.dll", 10605),
    "regional-options": ("intl.cpl", 200),
    "network-connections": ("ncpa.cpl", 1001),
    "taskbar-properties": ("shell32.dll", 40),
    "display-properties": ("desk.cpl", 100),
    "accessibility-options": ("access.cpl", 110),
    "volume-control": ("sndvol32.exe", 304),
    "mstsc": ("mstsc.exe", None),
    "winmine": ("winmine.exe", None),
    "sol": ("sol.exe", None),
    "mspaint": ("mspaint.exe", None),
    "email": ("shell32.dll", 265),
    "text-x-generic": ("shell32.dll", 152),
    "application-x-executable": ("shell32.dll", 3),
    "application-x-sharedlib": ("shell32.dll", 154),
    "unknown": ("shell32.dll", 1),
    "image-x-generic": ("shimgvw.dll", 3),
    "image-jpeg": ("shimgvw.dll", 4),
    "image-tiff": ("shimgvw.dll", 5),
    "audio-x-generic": ("shell32.dll", 225),
    "video-x-generic": ("shell32.dll", 227),
    "text-html": ("url.dll", 102),
    "application-msword": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 201),
    "font-x-generic": ("fontext.dll", 2),
    "application-x-font-type1": ("fontext.dll", 3),
    "application-x-msi": ("msiexec.exe", 1),
    "application-vnd.openxmlformats-officedocument.wordprocessingml.document": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 215),
    "application-vnd.ms-word.document.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 217),
    "application-msword-template": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 202),
    "application-vnd.openxmlformats-officedocument.wordprocessingml.template": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 216),
    "application-vnd.ms-word.template.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 218),
    "application-vnd.oasis.opendocument.text": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/wordicon.exe", 219),
    "application-vnd.ms-excel": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 288),
    "application-vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 258),
    "application-vnd.ms-excel.sheet.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 290),
    "application-vnd.ms-excel.sheet.binary.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 287),
    "application-vnd.openxmlformats-officedocument.spreadsheetml.template": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 261),
    "application-vnd.ms-excel.template.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 291),
    "application-vnd.ms-excel.addin.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 263),
    "text-csv": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 266),
    "application-vnd.oasis.opendocument.spreadsheet": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/xlicons.exe", 292),
    "application-vnd.ms-powerpoint": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1317),
    "application-vnd.openxmlformats-officedocument.presentationml.presentation": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1310),
    "application-vnd.ms-powerpoint.presentation.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1319),
    "application-vnd.openxmlformats-officedocument.presentationml.slideshow": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1312),
    "application-vnd.ms-powerpoint.slideshow.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1304),
    "application-vnd.openxmlformats-officedocument.presentationml.template": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1311),
    "application-vnd.ms-powerpoint.template.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1318),
    "application-vnd.ms-powerpoint.addin.macroEnabled.12": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1315),
    "application-vnd.oasis.opendocument.presentation": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pptico.exe", 1320),
    "application-vnd.ms-officetheme": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/misc.exe", 911),
    "application-vnd.ms-access": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/accicons.exe", 163),
    "application-x-msaccess-accdb": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/accicons.exe", 101),
    "application-x-msaccess-accde": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/accicons.exe", 144),
    "application-x-msaccess-accdt": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/accicons.exe", 102),
    "application-x-msaccess-mde": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/accicons.exe", 162),
    "application-vnd.ms-publisher": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/pubs.exe", 102),
    "application-onenote": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/joticon.exe", 101),
    "application-x-onenote-toc": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/joticon.exe", 103),
    "application-vnd.ms-outlook": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/outicon.exe", 101),
    "application-vnd.ms-outlook-pst": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/outicon.exe", 105),
    "text-vcard": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/outicon.exe", 103),
    "text-calendar": ("installer/{90140000-0011-0000-0000-0000000ff1ce}/outicon.exe", 102),
    "application-vnd.ms-works": ("installer/{15bc8cd0-a65b-47d0-a2dd-90a824590fa8}/wkswp.exe", None),
    "dialog-information": ("user32.dll", 104),
    "dialog-warning": ("user32.dll", 101),
    "dialog-error": ("user32.dll", 103),
    "dialog-question": ("user32.dll", 102),
    "security-high": ("wuaucpl.cpl", 3),
    "security-medium": ("wuaucpl.cpl", 4),
    "security-low": ("wuaucpl.cpl", 5),
    "audio-volume-muted": ("sndvol32.exe", 303),
    "edit-copy": ("shell32.dll", 243),
    "edit-delete": ("shell32.dll", 240),
    "edit-find": ("shell32.dll", 23),
    "system-run": ("shell32.dll", 25),
    "help-about": ("shell32.dll", 1001),
    "go-up": ("shell32.dll", 255),
    "go-next": ("shell32.dll", 290),
    "media-playback-start": ("shell32.dll", 246),
    "process-stop": ("shell32.dll", 200),
    "system-shutdown": ("shell32.dll", 28),
    "system-log-out": ("shell32.dll", 45),
    "system-lock-screen": ("shell32.dll", 48),
    "emblem-shared": ("shell32.dll", 29),
    "task-rename": ("shell32.dll", 153),
    "task-move": ("shell32.dll", 264),
    "task-copy": ("shell32.dll", 133),
    "task-slideshow": ("shell32.dll", 141),
    "delete-file": ("shell32.dll", 142),
    "delete-folder": ("shell32.dll", 143),
    "delete-many": ("shell32.dll", 144),
    "appearance-and-themes": ("shell32.dll", 239),
    "internet": ("shell32.dll", 14),
    "tray-volume": ("stobject.dll", 230),
    "tray-volume-muted": ("stobject.dll", 231),
    "tray-mic": ("sapi.cpl", 101),
    "tray-network": ("netshell.dll", 193),
    "tray-network-tx": ("netshell.dll", 191),
    "tray-network-rx": ("netshell.dll", 192),
    "tray-network-off": ("netshell.dll", 195),
    "tray-network-busy": ("netshell.dll", 196),
    "tray-bluetooth": ("irprops.cpl", 151),
    "ie-zone-internet": ("inetcpl.cpl", 1313),
    "ie-status-lock": ("shdocvw.dll", 103),
    "ie-popup-blocked": ("xpsp2res.dll", 5410),
    "ie-infobar-warning": ("xpsp2res.dll", 16),
    "ie-page": ("iexplore.exe", 32529),
    "ie-downloads": ("shdocvw.dll", 113),
    "ie-history-day": ("shdocvw.dll", 20783),
    "shortcut-overlay": ("shell32.dll", 30),
}

# --------------------------------------------------------------------------
# Imagens das DLL/EXE (assets/images/<área>/<nome>.png): bitmaps (RT_BITMAP)
# convertidos para PNG com a transparência que tinham (32 bits: alfa; os
# outros opacos — a cor-chave, quando há, tira-se ao usar).
# --------------------------------------------------------------------------
IMAGES = {
    # barra de tarefas
    "taskbar/start-flag": ("explorer.exe", 143),          # bandeira do botão Iniciar
    "taskbar/battery-icons": ("batmeter.dll", 301),       # tira 16x16: estados da bateria
    # Explorador
    "explorer/toolbar": ("shell32.dll", 214),             # botões 24x24 (Retroceder, Acima...)
    "explorer/toolbar-hot": ("shell32.dll", 215),
    "explorer/go": ("shell32.dll", 230),                  # "Ir para" da barra de endereço
    "explorer/go-hot": ("shell32.dll", 231),
    "explorer/brand": ("shell32.dll", 240),               # bandeira animada: 50 x 22x22
    # janela Abrir/Guardar como (botões 16x16 da barra)
    "file-dialog/toolbar": ("shell32.dll", 216),
    "file-dialog/toolbar-hot": ("shell32.dll", 217),
    # Internet Explorer 6
    "ie/toolbar": ("shell32.dll", 204),                   # botões 24x24 do IE6 Luna
    "ie/toolbar-hot": ("shell32.dll", 205),
    "ie/toolbar-small": ("shell32.dll", 206),             # os mesmos a 16x16
    "ie/explorer-bar": ("shdocvw.dll", 534),              # Adicionar, Organizar, Ver (18x16)
    "ie/explorer-bar-hot": ("shdocvw.dll", 535),
    "ie/search-bar": ("browseui.dll", 563),               # Procurar (18x16)
    "ie/search-bar-hot": ("browseui.dll", 564),
    # Windows Media Player 9 embutido (wmploc.dll): barra e botões redondos
    "wmp/bar": ("wmploc.dll", 371),
    "wmp/play": ("wmploc.dll", 373), "wmp/play-hover": ("wmploc.dll", 374),
    "wmp/play-down": ("wmploc.dll", 375), "wmp/play-disabled": ("wmploc.dll", 376),
    "wmp/pause": ("wmploc.dll", 427), "wmp/pause-hover": ("wmploc.dll", 423),
    "wmp/pause-down": ("wmploc.dll", 424),
    "wmp/prev": ("wmploc.dll", 381), "wmp/prev-hover": ("wmploc.dll", 382),
    "wmp/prev-down": ("wmploc.dll", 383), "wmp/prev-disabled": ("wmploc.dll", 384),
    "wmp/next": ("wmploc.dll", 395), "wmp/next-hover": ("wmploc.dll", 396),
    "wmp/next-down": ("wmploc.dll", 397), "wmp/next-disabled": ("wmploc.dll", 398),
    "wmp/mute": ("wmploc.dll", 365), "wmp/mute-hover": ("wmploc.dll", 366),
    "wmp/mute-down": ("wmploc.dll", 367), "wmp/mute-disabled": ("wmploc.dll", 368),
    # ecrã de boas-vindas (logonui.exe)
    "logon/glow": ("logonui.exe", 100),
    "logon/edit": ("logonui.exe", 102),                   # caixa da palavra-passe (9 partes)
    "logon/go": ("logonui.exe", 103), "logon/go-focus": ("logonui.exe", 104),
    "logon/info": ("logonui.exe", 105), "logon/info-focus": ("logonui.exe", 106),
    "logon/power": ("logonui.exe", 107), "logon/power-hot": ("logonui.exe", 121),
    "logon/undock": ("logonui.exe", 108), "logon/undock-hot": ("logonui.exe", 122),
    "logon/select": ("logonui.exe", 112),                 # utilizador escolhido
    "logon/frame": ("logonui.exe", 113), "logon/frame-hot": ("logonui.exe", 119),
    "logon/picture": ("logonui.exe", 114),
    "logon/logo": ("logonui.exe", 123),
    "logon/divider-v": ("logonui.exe", 124),
    "logon/divider-top": ("logonui.exe", 125),
    "logon/divider-bottom": ("logonui.exe", 126),
    # diálogos Desligar o computador (msgina.dll) e Terminar sessão (shell32)
    "logoff/background": ("msgina.dll", 20142),
    "logoff/flag": ("msgina.dll", 20143),
    "logoff/turnoff-icons": ("msgina.dll", 20150),        # tira 32x32: normal, premido, rato por cima
    "logoff/logoff-icons": ("shell32.dll", 14356),
}

# Bitmaps guardados tal e qual (assets/images/<área>/<nome>.bmp): o ecrã de
# arranque do ntoskrnl.exe tem as paletas a zero e o tools/builders/bootscreen.py
# põe-lhes a paleta à mão (a do bitmap 5, deslocada)
RAW_BITMAPS = {
    "boot/screen": ("ntoskrnl.exe", 1),                   # 640x480, 4 bits
    "boot/palette-source": ("ntoskrnl.exe", 5),
    "boot/progress": ("ntoskrnl.exe", 8),                 # três blocos de 22x9
}

# --------------------------------------------------------------------------
# Textos (assets/locales/<língua>/<ficheiro>.json): de cada um destes, todos
# os textos (string tables), diálogos (DIALOGEX, com as medidas em DLU) e
# menus (com o id de cada item), pelo id — que é o mesmo em todas as línguas
# do XP. A língua é a da cópia do Windows (--locale do extract.py).
# --------------------------------------------------------------------------
TEXT_FILES = [
    "comdlg32.dll",     # janela Abrir/Guardar como
    "shell32.dll",      # Explorador, Procurar pasta, eliminar, Terminar sessão
    "user32.dll",       # botões e títulos das caixas de mensagem
    "logonui.exe",      # ecrã de boas-vindas
    "winlogon.exe",     # "A iniciar o Windows...", "A terminar a sessão..."
    "msgina.dll",       # Desligar o computador
    "explorer.exe",     # barra de tarefas: o texto do botão Iniciar
]

# Páginas e imagens com nome (não numeradas) dentro das DLL:
# a página de erro de rede do IE6 (o texto, que é da língua do Windows)...
LOCALE_FILES = {
    "ie/dnserror.htm": ("shdoclc.dll", "DNSERROR.HTM"),
}
# ... e as suas imagens (iguais em todas as línguas: assets/images)
NAMED_IMAGES = {
    "ie/pagerror.gif": ("shdoclc.dll", "PAGERROR.GIF"),
    "ie/refresh.gif": ("shdoclc.dll", "REFRESH.GIF"),
    "ie/search.gif": ("shdoclc.dll", "SEARCH.GIF"),
    "ie/back.gif": ("shdoclc.dll", "BACK.GIF"),
}

# Textos que no XP vêm do registo (system32/config/<ficheiro>; HKCR =
# software\Classes), para assets/locales/<língua>/registry.json
REGISTRY_TEXTS = {
    "folder-type": ("software", r"Classes\Directory", ""),   # "Pasta de ficheiros"
}
