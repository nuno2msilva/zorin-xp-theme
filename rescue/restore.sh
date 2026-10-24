#!/usr/bin/env bash
# Zorin XP — EMERGENCY EXIT.
# Restores the system theme as it was in the "original" snapshot
# (or another one: ./restore.sh 20261011-170000) and removes everything the XP theme installed.
# Also works from a TTY (Ctrl+Alt+F3), with the graphical session open.
# install.sh leaves a copy (with the helpers this script calls) in
# ~/.local/share/zorin-xp/uninstall/rescue/restore.sh: it does not need the
# project folder.
set -uo pipefail

STATE_DIR="$HOME/.local/share/zorin-xp"
SNAP="${1:-original}"
SRC="$STATE_DIR/backup/$SNAP"
MANIFEST="$STATE_DIR/installed-files.txt"

if [ ! -d "$SRC" ]; then
    echo "Snapshot '$SNAP' não encontrado em $STATE_DIR/backup/" >&2
    ls "$STATE_DIR/backup/" 2>/dev/null
    exit 1
fi

if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

echo "A repor snapshot: $(readlink -f "$SRC")"

# 0. Applications with a browser engine: restore launchers and Flatpak overrides
if [ -f "$STATE_DIR/browser-fonts.txt" ]; then
    python3 "$(dirname "$0")/../src/fontconfig/zorin-xp-browser-fonts" --undo
fi

# 0. Flatpaks given the XP file dialog's GTK module (filechooser component)
if [ -f "$STATE_DIR/filechooser-flatpaks.txt" ] && command -v flatpak >/dev/null; then
    while read -r app path; do
        if [ "$app" = global ]; then
            # (only our two entries leave the global overrides: the rest stays)
            python3 - "$HOME/.local/share/flatpak/overrides/global" "$path" <<'PY'
import sys
from gi.repository import GLib
f, path = sys.argv[1], sys.argv[2]
kf = GLib.KeyFile()
try:
    kf.load_from_file(f, GLib.KeyFileFlags.KEEP_COMMENTS)
except GLib.Error:
    sys.exit(0)
try:
    kf.remove_key("Environment", "GTK3_MODULES")
except GLib.Error:
    pass
try:
    fs = [x for x in kf.get_string("Context", "filesystems").split(";") if x and x != path]
    if fs:
        kf.set_string("Context", "filesystems", ";".join(fs) + ";")
    else:
        kf.remove_key("Context", "filesystems")
except GLib.Error:
    pass
kf.save_to_file(f)
PY
            echo "  flatpak reposto: módulo do diálogo de ficheiros (global)"
        elif [ -n "$app" ]; then
            flatpak override --user --unset-env=GTK3_MODULES "$app" && echo "  flatpak reposto: $app"
        fi
    done < "$STATE_DIR/filechooser-flatpaks.txt"
fi

# 0. Files (XP Explorer): the previous list of types without thumbnails
[ -f "$STATE_DIR/explorer.json" ] && python3 "$(dirname "$0")/../tools/setup/explorerprefs.py" undo

# 0a. Zen Browser: previous preferences and the @import rules of the IE look
for P in "$HOME"/.var/app/app.zen_browser.zen/.zen/*/; do
    [ -f "$P/zorin-xp-ie.json" ] && python3 "$(dirname "$0")/../tools/setup/zenprefs.py" undo "$P"
    for UC in "$P/chrome/userChrome.css" "$P/chrome/userContent.css"; do
        if [ -f "$UC" ]; then
            sed -i '/^\/\* >>> zorin-xp: Internet Explorer/,/^\/\* <<< zorin-xp \*\//d' "$UC"
            [ -s "$UC" ] || rm -f "$UC"
        fi
    done
done

# 0b. Login screen (in the gdm user's folder: needs sudo)
if [ -f "$STATE_DIR/logon-installed" ]; then
    if sudo "$(dirname "$0")/../system/logon.sh" remove; then
        rm -f "$STATE_DIR/logon-installed"
    else
        echo "  ecrã de início de sessão NÃO reposto: sudo system/logon.sh remove" >&2
    fi
fi

# 0c. Boot screen (Plymouth, with sudo)
if [ -f "$STATE_DIR/boot-installed" ]; then
    if sudo "$(dirname "$0")/../system/bootscreen.sh" remove; then
        rm -f "$STATE_DIR/boot-installed"
    else
        echo "  ecrã de arranque NÃO reposto: sudo system/bootscreen.sh remove" >&2
    fi
fi

# 0d. Loading screen block in ~/.xprofile (the file itself, if the
#     installer created it, goes with the manifest)
if [ -f "$HOME/.xprofile" ]; then
    sed -i '/^# >>> zorin-xp/,/^# <<< zorin-xp/d' "$HOME/.xprofile"
fi

# 0e. Home folders with the XP names: back to the previous names
python3 "$(dirname "$0")/../tools/setup/xpfolders.py" undo
# ...and the desktop labels block in the GTK 3 gtk.css
GTK3CSS="$HOME/.config/gtk-3.0/gtk.css"
if [ -f "$GTK3CSS" ]; then
    sed -i '/^\/\* >>> zorin-xp: ícones do ambiente de trabalho/,/^\/\* <<< zorin-xp \*\//d' "$GTK3CSS"
    [ -s "$GTK3CSS" ] || rm -f "$GTK3CSS"
fi

# 1. Remove everything the XP installer recorded in the manifest
if [ -f "$MANIFEST" ]; then
    tac "$MANIFEST" | while IFS= read -r path; do
        case "$path" in
            "$HOME"/*) ;;                      # only deletes inside the home folder
            *) echo "  ignorado (fora da home): $path"; continue ;;
        esac
        if [ -e "$path" ] || [ -L "$path" ]; then
            rm -rf -- "$path" && echo "  removido: $path"
        fi
    done
    mv "$MANIFEST" "$MANIFEST.restored-$(date +%Y%m%d-%H%M%S)"
fi

# 1a. User file types: rebuild the database without Zorin XP's
[ -d "$HOME/.local/share/mime/packages" ] && update-mime-database "$HOME/.local/share/mime" 2>/dev/null

# 1b. File chooser portal: the service goes back to reading only the system folder
systemctl --user daemon-reload 2>/dev/null
systemctl --user try-restart xdg-desktop-portal.service 2>/dev/null

# 2. Restore the GTK config files (or delete them if they did not exist)
while read -r state f; do
    if [ "$state" = present ]; then
        mkdir -p "$(dirname "$f")"
        cp -a "$SRC/files$f" "$f" && echo "  reposto: $f"
    elif [ -e "$f" ]; then
        rm -f -- "$f" && echo "  removido (não existia antes): $f"
    fi
done < "$SRC/files.list"

# 3. Restore the dconf settings (reset the branch + load the snapshot)
for ini in "$SRC"/dconf/*.ini; do
    p="$(cat "${ini%.ini}.path")"
    dconf reset -f "$p"
    dconf load "$p" < "$ini"
    echo "  dconf reposto: $p"
done

fc-cache -f >/dev/null 2>&1 || true

echo
echo "Feito. Para recarregar o GNOME Shell (X11): Alt+F2, escrever 'r', Enter."
echo "A partir de um TTY: termine sessão e volte a entrar (ou: loginctl terminate-user $USER)."
