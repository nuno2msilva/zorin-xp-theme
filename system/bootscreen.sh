#!/usr/bin/env bash
# Zorin XP — the Windows XP boot screen (Plymouth theme).
#
# Plymouth only looks for themes in /usr/share/plymouth/themes and the theme
# goes into the initramfs, so this needs root. The only exception to the rule
# of not touching /usr/share (authorised): a NEW folder, windows-xp, without
# changing anything that is already there. The theme is chosen with the
# system's update-alternatives (default.plymouth), and removal returns it to
# automatic mode (the Zorin theme).
#
# Usage:  sudo system/bootscreen.sh install <build/boot>
#         sudo system/bootscreen.sh remove

set -euo pipefail

NAME=windows-xp
DIR=/usr/share/plymouth/themes/$NAME
LINK=/usr/share/plymouth/themes/default.plymouth

[ "$(id -u)" -eq 0 ] || { echo "Correr com sudo." >&2; exit 1; }

case "${1:-}" in
install)
    src="${2:?pasta build/boot}"
    [ -f "$src/$NAME/$NAME.script" ] || { echo "Falta $src/$NAME (correr o build)." >&2; exit 1; }
    rm -rf "$DIR"
    cp -r "$src/$NAME" "$DIR"
    chmod -R u=rwX,go=rX "$DIR"
    update-alternatives --install "$LINK" default.plymouth "$DIR/$NAME.plymouth" 300 \
        --slave /usr/share/plymouth/themes/default.grub default.plymouth.grub "$DIR/$NAME.grub"
    update-alternatives --set default.plymouth "$DIR/$NAME.plymouth"
    echo "A atualizar o initramfs (pode demorar um minuto)..."
    update-initramfs -u
    echo "Ecrã de arranque do XP instalado (aparece no próximo arranque)."
    ;;
remove)
    if [ -d "$DIR" ]; then
        update-alternatives --remove default.plymouth "$DIR/$NAME.plymouth" || true
        rm -rf "$DIR"
        echo "A atualizar o initramfs..."
        update-initramfs -u
    fi
    echo "Ecrã de arranque reposto."
    ;;
*)
    echo "Uso: sudo $0 install <build/boot> | remove" >&2; exit 1 ;;
esac
