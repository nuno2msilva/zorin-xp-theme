#!/usr/bin/env bash
# Zorin XP — SAÍDA DE EMERGÊNCIA.
# Repõe o tema do sistema tal como estava no snapshot "original"
# (ou noutro: ./restore.sh 20261011-170000) e remove tudo o que o tema XP instalou.
# Funciona também a partir de um TTY (Ctrl+Alt+F3), com a sessão gráfica aberta.
# O install.sh deixa uma cópia (com os ajudantes que este script chama) em
# ~/.local/share/zorin-xp/uninstall/rescue/restore.sh: não precisa da pasta
# do projeto.
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

# 0. Aplicações com motor de browser: repor lançadores e overrides do Flatpak
if [ -f "$STATE_DIR/browser-fonts.txt" ]; then
    python3 "$(dirname "$0")/../src/fontconfig/zorin-xp-browser-fonts" --undo
fi

# 0. Ficheiros (Explorador do XP): a lista de tipos sem miniatura de antes
[ -f "$STATE_DIR/explorer.json" ] && python3 "$(dirname "$0")/../tools/setup/explorerprefs.py" undo

# 0a. Zen Browser: preferências antigas e os @import do aspeto do IE
for P in "$HOME"/.var/app/app.zen_browser.zen/.zen/*/; do
    [ -f "$P/zorin-xp-ie.json" ] && python3 "$(dirname "$0")/../tools/setup/zenprefs.py" undo "$P"
    for UC in "$P/chrome/userChrome.css" "$P/chrome/userContent.css"; do
        if [ -f "$UC" ]; then
            sed -i '/^\/\* >>> zorin-xp: Internet Explorer/,/^\/\* <<< zorin-xp \*\//d' "$UC"
            [ -s "$UC" ] || rm -f "$UC"
        fi
    done
done

# 0b. Ecrã de início de sessão (na pasta do utilizador gdm: precisa de sudo)
if [ -f "$STATE_DIR/logon-installed" ]; then
    if sudo "$(dirname "$0")/../system/logon.sh" remove; then
        rm -f "$STATE_DIR/logon-installed"
    else
        echo "  ecrã de início de sessão NÃO reposto: sudo system/logon.sh remove" >&2
    fi
fi

# 0c. Ecrã de arranque (Plymouth, com sudo)
if [ -f "$STATE_DIR/boot-installed" ]; then
    if sudo "$(dirname "$0")/../system/bootscreen.sh" remove; then
        rm -f "$STATE_DIR/boot-installed"
    else
        echo "  ecrã de arranque NÃO reposto: sudo system/bootscreen.sh remove" >&2
    fi
fi

# 0d. Bloco do ecrã de carregamento no ~/.xprofile (o ficheiro, se foi o
#     instalador que o criou, sai com o manifesto)
if [ -f "$HOME/.xprofile" ]; then
    sed -i '/^# >>> zorin-xp/,/^# <<< zorin-xp/d' "$HOME/.xprofile"
fi

# 0e. Pastas pessoais com os nomes do XP: voltam aos nomes de antes
python3 "$(dirname "$0")/../tools/setup/xpfolders.py" undo
# ...e o bloco das legendas do ambiente de trabalho no gtk.css do GTK 3
GTK3CSS="$HOME/.config/gtk-3.0/gtk.css"
if [ -f "$GTK3CSS" ]; then
    sed -i '/^\/\* >>> zorin-xp: ícones do ambiente de trabalho/,/^\/\* <<< zorin-xp \*\//d' "$GTK3CSS"
    [ -s "$GTK3CSS" ] || rm -f "$GTK3CSS"
fi

# 1. Remover tudo o que o instalador XP registou no manifesto
if [ -f "$MANIFEST" ]; then
    tac "$MANIFEST" | while IFS= read -r path; do
        case "$path" in
            "$HOME"/*) ;;                      # só apaga dentro da home
            *) echo "  ignorado (fora da home): $path"; continue ;;
        esac
        if [ -e "$path" ] || [ -L "$path" ]; then
            rm -rf -- "$path" && echo "  removido: $path"
        fi
    done
    mv "$MANIFEST" "$MANIFEST.restored-$(date +%Y%m%d-%H%M%S)"
fi

# 1a. Tipos de ficheiro do utilizador: refazer a base sem os do Zorin XP
[ -d "$HOME/.local/share/mime/packages" ] && update-mime-database "$HOME/.local/share/mime" 2>/dev/null

# 1b. Portal de ficheiros: o serviço volta a ler só a pasta do sistema
systemctl --user daemon-reload 2>/dev/null
systemctl --user try-restart xdg-desktop-portal.service 2>/dev/null

# 2. Repor os ficheiros de config do GTK (ou apagá-los se não existiam)
while read -r state f; do
    if [ "$state" = present ]; then
        mkdir -p "$(dirname "$f")"
        cp -a "$SRC/files$f" "$f" && echo "  reposto: $f"
    elif [ -e "$f" ]; then
        rm -f -- "$f" && echo "  removido (não existia antes): $f"
    fi
done < "$SRC/files.list"

# 3. Repor as definições dconf (reset do ramo + load do snapshot)
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
