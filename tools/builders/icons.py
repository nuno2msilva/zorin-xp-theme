"""The "WindowsXP" icon theme: XP's icons taken from the binaries.

Folders, places, devices, file types, status, actions, emblems and the
system applications (Files = Explorer, Settings = Control Panel, Text
Editor = Notepad, ...). The menu categories (applications-*) and the
symbolic icons stay Zorin's, from which the theme inherits everything else
(ZorinBlue-Light, Adwaita, hicolor).

Each freedesktop name points to an XP icon in assets/icons (the .ico's name;
the source of each is in tools/catalog.py), or to a composite icon
("composite:...", made here from XP pieces).
"""
import os

from PIL import Image

from lib import assets

ICONS = {
    "places": {
        "folder": "folder", "inode-directory": "folder", "folder-open": "folder-open",
        "folder-drag-accept": "folder-open", "folder-visiting": "folder-open",
        "folder-documents": "folder-documents", "folder-pictures": "folder-pictures",
        "folder-music": "folder-music", "folder-videos": "folder-videos",
        "folder-download": "composite:downloads", "folder-templates": "folder",
        "folder-publicshare": "folder-publicshare", "folder-remote": "folder-remote",
        "folder-saved-search": "folder-saved-search", "folder-recent": "folder-recent",
        "folder-new": "folder-new",
        "user-home": "computer", "user-desktop": "desktop",       # "O meu computador"
        "user-bookmarks": "favorites", "user-trash": "recycle-bin", "user-trash-full": "recycle-bin-full",
        "network-workgroup": "network-places", "network-server": "network-server",
        "start-here": "computer",
    },
    "devices": {
        "computer": "computer", "drive-harddisk": "drive-harddisk", "drive-harddisk-system": "drive-harddisk",
        "drive-harddisk-usb": "drive-removable", "drive-harddisk-ieee1394": "drive-removable",
        "drive-removable-media": "drive-removable", "drive-removable-media-usb": "drive-removable",
        "drive-optical": "drive-optical", "drive-multidisk": "drive-harddisk",
        "media-optical": "media-optical", "media-optical-cd": "media-optical-cd", "media-optical-cd-r": "media-optical-cd-r",
        "media-optical-cd-rw": "media-optical-cd-rw", "media-optical-dvd": "media-optical-dvd",
        "media-optical-dvd-r": "media-optical-dvd-r", "media-optical-dvd-rw": "media-optical-dvd-rw",
        "media-optical-cd-audio": "media-optical-cd-audio", "media-floppy": "media-floppy", "media-flash": "media-flash",
        "media-zip": "media-zip", "media-removable": "drive-removable",
        "printer": "printer", "printer-network": "printer-network", "scanner": "scanner",
        "camera-photo": "camera-photo", "camera-video": "camera-video", "camera-web": "camera-web",
        "phone": "phone", "pda": "pda", "multimedia-player": "multimedia-player",
        "input-mouse": "input-mouse", "input-keyboard": "input-keyboard",
        "input-gaming": "input-gaming", "input-tablet": "input-mouse",
        "audio-card": "audio-card", "audio-speakers": "audio-speakers",
        "audio-headphones": "audio-speakers", "audio-input-microphone": "audio-input-microphone",
        "video-display": "video-display", "display": "video-display",
        "battery": "battery", "uninterruptible-power-supply": "uninterruptible-power-supply",
        "network-wired": "network-wired", "network-wireless": "network-wireless",
        "modem": "modem", "bluetooth": "bluetooth",
        "computer-laptop": "computer",
    },
    "apps": {
        # system applications -> the equivalent XP programs
        "org.gnome.Nautilus": "explorer", "system-file-manager": "explorer",
        "org.gnome.Settings": "control-panel", "preferences-system": "control-panel",
        "gnome-control-center": "control-panel",
        "org.gnome.Terminal": "cmd", "utilities-terminal": "cmd",
        "org.gnome.Console": "cmd",
        "org.gnome.TextEditor": "notepad", "org.gnome.gedit": "notepad",
        "accessories-text-editor": "notepad",
        "org.gnome.Calculator": "calc", "accessories-calculator": "calc",
        "org.gnome.Characters": "charmap", "accessories-character-map": "charmap",
        "org.gnome.font-viewer": "fonts-folder", "preferences-desktop-font": "fonts-folder",
        "org.gnome.baobab": "cleanmgr", "org.gnome.DiskUtility": "disk-management",
        "org.gnome.eog": "picture-viewer", "org.gnome.Loupe": "picture-viewer",
        "org.gnome.Evince": "document", "org.gnome.Papers": "document",
        "org.gnome.FileRoller": "compressed-folder",
        "org.gnome.Logs": "eventvwr", "org.gnome.PowerStats": "battery",
        "org.gnome.Rhythmbox3": "media-player", "org.gnome.Totem": "media-player",
        "org.gnome.seahorse.Application": "passwords",
        "org.gnome.Software": "add-remove-programs", "system-software-install": "add-remove-programs",
        "software-properties": "automatic-updates", "system-software-update": "automatic-updates",
        "update-manager": "automatic-updates", "zorin-os-upgrader": "automatic-updates",
        "org.gnome.SoundRecorder": "sndrec32", "audio-recorder": "sndrec32",
        "org.gnome.SystemMonitor": "taskmgr", "utilities-system-monitor": "taskmgr",
        "org.gnome.Yelp": "help-and-support", "help-browser": "help-and-support",
        "org.gnome.Calendar": "date-time", "org.gnome.clocks": "date-time",
        "org.gnome.Contacts": "user-accounts",
        "org.gnome.DejaDup": "ntbackup", "deja-dup": "ntbackup",
        "org.gnome.SimpleScan": "wiaacmgr", "org.gnome.Snapshot": "camera-photo",
        "org.gnome.Tour": "tourstart",
        "gufw": "firewall", "preferences-desktop-locale": "regional-options",
        "preferences-system-network": "network-connections", "ibus-setup": "input-keyboard",
        "alacarte": "taskbar-properties", "zorin-appearance": "display-properties",
        "preferences-desktop-display": "display-properties", "preferences-desktop-theme": "display-properties",
        "preferences-desktop-accessibility": "accessibility-options",
        "preferences-desktop-keyboard": "input-keyboard", "preferences-desktop-peripherals": "input-mouse",
        "preferences-system-time": "date-time", "preferences-system-power": "battery",
        "preferences-system-firewall": "firewall",
        "preferences-desktop-user": "user-accounts", "system-users": "user-accounts",
        "preferences-system-sound": "audio-speakers", "multimedia-volume-control": "volume-control",
        "org.gnome.Remmina": "mstsc", "org.remmina.Remmina": "mstsc",
        "gnome-mines": "winmine", "org.gnome.Mines": "winmine",
        "sol": "sol", "gnome-aisleriot": "sol", "org.gnome.Aisleriot": "sol",
        "accessories-screenshot": "mspaint", "org.gnome.Screenshot": "mspaint",
        "internet-mail": "email", "evolution": "email",
    },
    "mimetypes": {
        "inode-directory": "folder", "text-x-generic": "text-x-generic", "text-plain": "text-x-generic",
        "text-x-log": "text-x-generic", "text-x-generic-template": "text-x-generic",
        "application-x-executable": "application-x-executable", "application-x-ms-dos-executable": "application-x-executable",
        "application-x-msdownload": "application-x-executable", "application-x-sharedlib": "application-x-sharedlib",
        "unknown": "unknown", "application-octet-stream": "unknown",
        # images as in XP (associations of the Windows Picture and Fax Viewer,
        # shimgvw.dll): JPEG with the sunset, PNG/GIF/BMP with the shapes, TIFF
        "image-x-generic": "image-x-generic", "image-bmp": "image-x-generic",
        "image-png": "image-x-generic", "image-gif": "image-x-generic", "image-x-icon": "image-x-generic",
        "image-jpeg": "image-jpeg", "image-tiff": "image-tiff",
        "audio-x-generic": "audio-x-generic", "video-x-generic": "video-x-generic",
        "text-html": "text-html", "application-xhtml+xml": "text-html",
        "application-zip": "compressed-folder", "application-x-archive": "compressed-folder",
        "application-x-compressed-tar": "compressed-folder", "application-x-7z-compressed": "compressed-folder",
        "application-x-rar": "compressed-folder", "package-x-generic": "compressed-folder",
        "application-x-cd-image": "media-optical",
        "x-office-document": "document",         "font-x-generic": "font-x-generic", "application-x-font-ttf": "font-x-generic",
        "application-x-font-type1": "application-x-font-type1",
        "application-x-shellscript": "application-x-sharedlib", "text-x-script": "application-x-sharedlib",
                "message-rfc822": "email",
    },
    "status": {
        "dialog-information": "dialog-information", "dialog-warning": "dialog-warning",
        "dialog-error": "dialog-error", "dialog-question": "dialog-question",
        "security-high": "security-high", "security-medium": "security-medium",
        "security-low": "security-low",
        "audio-volume-high": "volume-control", "audio-volume-muted": "audio-volume-muted",
    },
    "actions": {
        "edit-copy": "edit-copy", "edit-delete": "edit-delete", "edit-find": "edit-find",
        "system-search": "edit-find", "system-run": "system-run", "help-contents": "help-and-support",
        "help-about": "help-about", "go-up": "go-up", "go-next": "go-next",
        "media-playback-start": "media-playback-start", "process-stop": "process-stop",
        "document-print": "printer", "folder-new": "folder-new",
        "system-shutdown": "system-shutdown", "system-log-out": "system-log-out", "system-lock-screen": "system-lock-screen",
        "mail-send": "email",
    },
    "emblems": {
        "emblem-symbolic-link": "composite:shortcut-arrow", "emblem-shared": "emblem-shared",
        "emblem-unreadable": "process-stop",
    },
}
# Office 2010 and Works as in the reference XP VM: each type's icon is the
# DefaultIcon from its registry (system32/config/software, HKCR\<ProgID>), in
# the icon files of the installer cache (WINDOWS\Installer\{product}); the
# installers (.msi and also .deb, .rpm, flatpak, snap) with the "Windows
# Installer Package" (msiexec.exe). Approved by the user (2026-10-17,
# Screenshots/proposta-icones.png); PDF is waiting for Adobe's files.
OFFICE = {
    # Word
    "application-msword": "application-msword", "application-rtf": "application-msword",
    "application-vnd.openxmlformats-officedocument.wordprocessingml.document": "application-vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application-vnd.ms-word.document.macroEnabled.12": "application-vnd.ms-word.document.macroEnabled.12",
    "application-msword-template": "application-msword-template",
    "application-vnd.openxmlformats-officedocument.wordprocessingml.template": "application-vnd.openxmlformats-officedocument.wordprocessingml.template",
    "application-vnd.ms-word.template.macroEnabled.12": "application-vnd.ms-word.template.macroEnabled.12",
    "application-vnd.oasis.opendocument.text": "application-vnd.oasis.opendocument.text",
    # Excel (.xlt, .xla, .xlw have the same type as .xls on the system)
    "application-vnd.ms-excel": "application-vnd.ms-excel",
    "application-vnd.openxmlformats-officedocument.spreadsheetml.sheet": "application-vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application-vnd.ms-excel.sheet.macroEnabled.12": "application-vnd.ms-excel.sheet.macroEnabled.12",
    "application-vnd.ms-excel.sheet.binary.macroEnabled.12": "application-vnd.ms-excel.sheet.binary.macroEnabled.12",
    "application-vnd.openxmlformats-officedocument.spreadsheetml.template": "application-vnd.openxmlformats-officedocument.spreadsheetml.template",
    "application-vnd.ms-excel.template.macroEnabled.12": "application-vnd.ms-excel.template.macroEnabled.12",
    "application-vnd.ms-excel.addin.macroEnabled.12": "application-vnd.ms-excel.addin.macroEnabled.12",
    "text-csv": "text-csv",
    "application-vnd.oasis.opendocument.spreadsheet": "application-vnd.oasis.opendocument.spreadsheet",
    "x-office-spreadsheet": "application-vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # PowerPoint (.pps, .pot have the same type as .ppt on the system)
    "application-vnd.ms-powerpoint": "application-vnd.ms-powerpoint",
    "application-vnd.openxmlformats-officedocument.presentationml.presentation": "application-vnd.openxmlformats-officedocument.presentationml.presentation",
    "application-vnd.ms-powerpoint.presentation.macroEnabled.12": "application-vnd.ms-powerpoint.presentation.macroEnabled.12",
    "application-vnd.openxmlformats-officedocument.presentationml.slideshow": "application-vnd.openxmlformats-officedocument.presentationml.slideshow",
    "application-vnd.ms-powerpoint.slideshow.macroEnabled.12": "application-vnd.ms-powerpoint.slideshow.macroEnabled.12",
    "application-vnd.openxmlformats-officedocument.presentationml.template": "application-vnd.openxmlformats-officedocument.presentationml.template",
    "application-vnd.ms-powerpoint.template.macroEnabled.12": "application-vnd.ms-powerpoint.template.macroEnabled.12",
    "application-vnd.ms-powerpoint.addin.macroEnabled.12": "application-vnd.ms-powerpoint.addin.macroEnabled.12",
    "application-vnd.oasis.opendocument.presentation": "application-vnd.oasis.opendocument.presentation",
    "x-office-presentation": "application-vnd.openxmlformats-officedocument.presentationml.presentation",
    "application-vnd.ms-officetheme": "application-vnd.ms-officetheme",
    # Access, Publisher, OneNote, Outlook (the types the system did not have:
    # src/mime/zorin-xp-office.xml)
    "application-vnd.ms-access": "application-vnd.ms-access", "application-x-msaccess-accdb": "application-x-msaccess-accdb",
    "application-x-msaccess-accde": "application-x-msaccess-accde", "application-x-msaccess-accdt": "application-x-msaccess-accdt",
    "application-x-msaccess-mde": "application-x-msaccess-mde",
    "application-vnd.ms-publisher": "application-vnd.ms-publisher",
    "application-onenote": "application-onenote", "application-x-onenote-toc": "application-x-onenote-toc",
    "application-vnd.ms-outlook": "application-vnd.ms-outlook", "application-vnd.ms-outlook-pst": "application-vnd.ms-outlook-pst",
    "text-vcard": "text-vcard", "text-x-vcard": "text-vcard", "text-calendar": "text-calendar",
    # Microsoft Works (Word Processor)
    "application-vnd.ms-works": "application-vnd.ms-works",
    # instaladores
    "application-x-msi": "application-x-msi", "application-vnd.debian.binary-package": "application-x-msi",
    "application-x-deb": "application-x-msi", "application-x-rpm": "application-x-msi",
    "application-x-redhat-package-manager": "application-x-msi", "application-vnd.flatpak": "application-x-msi",
    "application-vnd.flatpak.ref": "application-x-msi", "application-vnd.flatpak.repo": "application-x-msi",
    "application-vnd.snap": "application-x-msi",
}
ICONS["mimetypes"].update(OFFICE)

SIZES = (16, 32, 48)
# sizes XP does not have: the small ones centred (sharp, like XP's
# toolbars), the big ones scaled up to the pixel
EXTRA = {22: (16, "pad"), 24: (16, "pad"), 64: (32, 2), 96: (48, 2)}
CONTEXT = {"places": "Places", "devices": "Devices", "apps": "Applications",
           "mimetypes": "MimeTypes", "status": "Status", "actions": "Actions", "emblems": "Emblems"}


# icons composed from XP pieces (XP did not have these)
def _downloads(size):
    """"Downloads": the XP folder with the Internet Explorer globe (the user's
    choice, 2026-10-13)."""
    folder = image("folder", size).copy()
    globe = image("internet", 48)
    bs = round(size * 0.55)
    globe = globe.resize((bs, bs), Image.LANCZOS)
    folder.alpha_composite(globe, (round(size * 0.45), round(size * 0.42)))
    return folder


def _shortcut_arrow(size):
    """Shortcut emblem: only XP's arrow (shortcut-overlay), cropped. XP puts the
    whole overlay icon on top of the icon; GNOME draws the emblem in a square
    of 1/3 of the icon — with the whole overlay the arrow was tiny. XP's
    arrow takes ~1/3 of the icon (11 px in 32), so it ends up the right size."""
    # the biggest cropped arrow closest to the requested size (16 px: 7, 32: 11, 48: 20)
    crops = []
    for base in (16, 32, 48):
        im = image("shortcut-overlay", base)
        crops.append(im.crop(im.getchannel("A").getbbox()))
    arrow = next((c for c in crops if max(c.size) >= size), crops[-1])
    side = max(arrow.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(arrow, (0, side - arrow.height))
    if side == size:
        return sq
    method = Image.NEAREST if size % side == 0 else Image.LANCZOS
    return sq.resize((size, size), method)


COMPOSITES = {"downloads": _downloads, "shortcut-arrow": _shortcut_arrow}


def image(name, size):
    """An icon at one size: XP's (assets/icons/<name>.ico) or, if XP did not
    have it at that size, the biggest one it had, scaled down; "composite:..."
    is one of the composites above."""
    if name.startswith("composite:"):
        return COMPOSITES[name.split(":", 1)[1]](size)
    img = assets.icon(name, size)
    if img is None:
        big = next((assets.icon(name, s) for s in (48, 32, 16) if assets.icon(name, s)), None)
        img = big.resize((size, size), Image.LANCZOS) if big else None
    return img


# composites drawn directly at any size (without centring or scaling up)
DIRECT = {"composite:shortcut-arrow"}


def _render(name, size):
    if size in EXTRA and name not in DIRECT:
        base, how = EXTRA[size]
        img = image(name, base)
        if img is None:
            return None
        if how == "pad":
            out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            out.paste(img, ((size - base) // 2, (size - base) // 2))
            return out
        return img.resize((size, size), Image.NEAREST)
    return image(name, size)


def build(out_dir, name="WindowsXP"):
    """Icon theme in out_dir/<name>."""
    theme = os.path.join(out_dir, name)
    dirs = []
    for ctx, icons in ICONS.items():
        for size in sorted(SIZES + tuple(EXTRA)):
            d = f"{size}x{size}/{ctx}"
            os.makedirs(os.path.join(theme, d), exist_ok=True)
            dirs.append((d, size, ctx))
            for fd_name, icon in icons.items():
                img = _render(icon, size)
                if img:
                    img.save(os.path.join(theme, d, fd_name + ".png"))
    with open(os.path.join(theme, "index.theme"), "w") as f:
        f.write("[Icon Theme]\nName=Windows XP\nComment=Ícones do Windows XP\n"
                "Inherits=ZorinBlue-Light,Adwaita,hicolor\n"
                f"Directories={','.join(d for d, _, _ in dirs)}\n\n")
        for d, size, ctx in dirs:
            f.write(f"[{d}]\nSize={size}\nContext={CONTEXT[ctx]}\nType=Fixed\n\n")
    return theme
