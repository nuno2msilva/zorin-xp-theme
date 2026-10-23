#!/usr/bin/env bash
# Zorin XP — snapshot of the current theme, before any change.
# Saves the relevant dconf settings and the GTK config files in
# ~/.local/share/zorin-xp/backup/<date>/ and marks it as "original".
set -euo pipefail

STATE_DIR="$HOME/.local/share/zorin-xp"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$STATE_DIR/backup/$STAMP"

# dconf paths the XP theme may change
DCONF_PATHS=(
    /org/gnome/desktop/interface/
    /org/gnome/desktop/wm/preferences/
    /org/gnome/desktop/sound/
    /org/gnome/desktop/background/
    /org/gnome/desktop/screensaver/
    /org/gnome/shell/
    /org/gnome/mutter/
    /com/zorin/desktop/      # zorin-auto-theme puts the Zorin theme back at sunrise/sunset
    /org/gnome/nautilus/     # icon views and size (XP Explorer)
)

# User files the theme may create or replace
USER_FILES=(
    "$HOME/.config/gtk-3.0/gtk.css"
    "$HOME/.config/gtk-3.0/settings.ini"
    "$HOME/.config/gtk-4.0/gtk.css"
    "$HOME/.config/gtk-4.0/settings.ini"
    "$HOME/.gtkrc-2.0"
    "$HOME/.icons/default/index.theme"
)

# Allows running from a TTY by connecting to the graphical session's bus
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

mkdir -p "$DEST/dconf" "$DEST/files"

for p in "${DCONF_PATHS[@]}"; do
    name="$(echo "$p" | sed 's#^/##; s#/$##; s#/#_#g')"
    dconf dump "$p" > "$DEST/dconf/$name.ini"
    echo "$p" > "$DEST/dconf/$name.path"
done

# Full copy of the dconf database (last resort)
cp -a "$HOME/.config/dconf/user" "$DEST/dconf-user.raw" 2>/dev/null || true

: > "$DEST/files.list"
for f in "${USER_FILES[@]}"; do
    if [ -e "$f" ]; then
        mkdir -p "$DEST/files$(dirname "$f")"
        cp -a "$f" "$DEST/files$f"
        echo "present $f" >> "$DEST/files.list"
    else
        echo "absent $f" >> "$DEST/files.list"
    fi
done

# The first snapshot is the "original" one; it is never overwritten
if [ ! -e "$STATE_DIR/backup/original" ]; then
    ln -s "$STAMP" "$STATE_DIR/backup/original"
    echo "Snapshot ORIGINAL guardado em $DEST"
else
    echo "Snapshot adicional guardado em $DEST (o original mantém-se: $(readlink "$STATE_DIR/backup/original"))"
fi
