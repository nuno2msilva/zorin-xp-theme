#!/usr/bin/env bash
# Zorin XP — snapshot do tema atual, antes de qualquer alteração.
# Guarda as definições dconf relevantes e os ficheiros de config do GTK
# em ~/.local/share/zorin-xp/backup/<data>/ e marca-o como "original".
set -euo pipefail

STATE_DIR="$HOME/.local/share/zorin-xp"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$STATE_DIR/backup/$STAMP"

# Caminhos dconf que o tema XP pode alterar
DCONF_PATHS=(
    /org/gnome/desktop/interface/
    /org/gnome/desktop/wm/preferences/
    /org/gnome/desktop/sound/
    /org/gnome/desktop/background/
    /org/gnome/desktop/screensaver/
    /org/gnome/shell/
    /org/gnome/mutter/
    /com/zorin/desktop/      # zorin-auto-theme repõe o tema Zorin ao nascer/pôr do sol
    /org/gnome/nautilus/     # vistas e tamanho dos ícones (Explorador do XP)
)

# Ficheiros de utilizador que o tema pode criar ou substituir
USER_FILES=(
    "$HOME/.config/gtk-3.0/gtk.css"
    "$HOME/.config/gtk-3.0/settings.ini"
    "$HOME/.config/gtk-4.0/gtk.css"
    "$HOME/.config/gtk-4.0/settings.ini"
    "$HOME/.gtkrc-2.0"
    "$HOME/.icons/default/index.theme"
)

# Permite correr a partir de um TTY ligando-se ao bus da sessão gráfica
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

mkdir -p "$DEST/dconf" "$DEST/files"

for p in "${DCONF_PATHS[@]}"; do
    name="$(echo "$p" | sed 's#^/##; s#/$##; s#/#_#g')"
    dconf dump "$p" > "$DEST/dconf/$name.ini"
    echo "$p" > "$DEST/dconf/$name.path"
done

# Cópia integral da base de dados dconf (último recurso)
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

# O primeiro snapshot é o "original"; nunca é sobrescrito
if [ ! -e "$STATE_DIR/backup/original" ]; then
    ln -s "$STAMP" "$STATE_DIR/backup/original"
    echo "Snapshot ORIGINAL guardado em $DEST"
else
    echo "Snapshot adicional guardado em $DEST (o original mantém-se: $(readlink "$STATE_DIR/backup/original"))"
fi
