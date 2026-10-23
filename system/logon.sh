#!/usr/bin/env bash
# Zorin XP — the XP welcome screen on the login screen (GDM).
#
# The login screen runs as the "gdm" user, so this needs root. It does not
# touch /usr; almost everything goes into the gdm user's folder
# (/var/lib/gdm3), as if it were that user's personal configuration:
#   .local/share/gnome-shell/extensions/zorin-xp-logon@zorin-xp.local
#   .local/share/fonts/zorin-xp           (XP Tahoma and Arial)
#   .config/fontconfig/conf.d/6x-*.conf   (XP font sharpness)
#   .local/share/icons/WindowsXP-Cursors  (XP cursors, if installed)
#   .icons/WindowsXP-Cursors              (link: Xcursor only looks there)
#   .config/environment.d/60-zorin-xp-freetype.conf (v35 interpreter)
#   gdm's dconf: enabled-extensions, cursor-theme, cursor-size, font-hinting,
#                font-antialiasing
# The previous values are kept in .local/share/zorin-xp-logon/previous.
# (An earlier version put a marked block in /etc/gdm3/Prime/Default;
# install and remove take it out if it is there.)
#
# Usage:  sudo system/logon.sh install <build/logon> [<XP cursors folder>]
#         sudo system/logon.sh remove
# Takes effect the next time the login screen appears.
#
# Emergency (the screen does not let you in): Ctrl+Alt+F3, log in on the terminal and
#   sudo <project folder>/system/logon.sh remove && sudo systemctl restart gdm3
set -euo pipefail

UUID=zorin-xp-logon@zorin-xp.local
if [ -n "${ZXP_TEST_HOME:-}" ]; then
    # dry run without root: any folder can stand in for gdm's folder
    GDM_USER=$(id -un); GDM_HOME=$ZXP_TEST_HOME
elif getent passwd gdm >/dev/null; then GDM_USER=gdm; else GDM_USER=Debian-gdm; fi
GDM_HOME=${GDM_HOME:-$(getent passwd "$GDM_USER" | cut -d: -f6)}
STATE=$GDM_HOME/.local/share/zorin-xp-logon
EXT=$GDM_HOME/.local/share/gnome-shell/extensions/$UUID
FONTS=$GDM_HOME/.local/share/fonts/zorin-xp
FC=$GDM_HOME/.config/fontconfig/conf.d
CURSORS=$GDM_HOME/.local/share/icons/WindowsXP-Cursors
# (Xcursor — which gives the login screen its cursors — only looks in
# ~/.icons and /usr/share/icons: without this link the system ones stayed)
CURSORS_LINK=$GDM_HOME/.icons/WindowsXP-Cursors
FC_FILES=(60-windows-xp.conf 61-windows-xp-arial.conf)
# XP's TrueType interpreter (strokes snapped to the pixel, like GDI)
ENVD=$GDM_HOME/.config/environment.d/60-zorin-xp-freetype.conf
SPLASH=$GDM_HOME/.local/bin/zorin-xp-splash
PRIME=${ZXP_TEST_PRIME:-/etc/gdm3/Prime/Default}
[ -n "${ZXP_TEST_HOME:-}" ] && [ -z "${ZXP_TEST_PRIME:-}" ] && PRIME=
BEGIN='# >>> zorin-xp: ecrã do XP enquanto o greeter arranca (system/logon.sh)'
END='# <<< zorin-xp'

[ "$(id -u)" -eq 0 ] || [ -n "${ZXP_TEST_HOME:-}" ] || { echo "Correr com sudo." >&2; exit 1; }
[ -d "$GDM_HOME" ] || { echo "Utilizador do GDM não encontrado." >&2; exit 1; }

as_gdm() {  # as GDM itself does (/usr/share/gdm/generate-config)
    if [ -n "${ZXP_TEST_HOME:-}" ]; then
        env -i PATH=/usr/bin:/bin HOME="$GDM_HOME" XDG_CONFIG_HOME="$GDM_HOME/.config" \
            XDG_DATA_HOME="$GDM_HOME/.local/share" XDG_CACHE_HOME="$GDM_HOME/.cache" "$@"
        return
    fi
    setpriv --reuid "$GDM_USER" --regid "$GDM_USER" --init-groups --reset-env \
        env HOME="$GDM_HOME" "$@"
}
gs() {  # (the private bus's dbus-daemon logs each activation on stderr: left out)
    local err rc
    { err=$(as_gdm dbus-run-session -- gsettings "$@" 2>&1 >&3); rc=$?; } 3>&1 || true
    [ -z "$err" ] || grep -v '^dbus-daemon\[' <<<"$err" >&2 || true
    return $rc
}
gdm_dir() { install -d -o "$GDM_USER" -g "$GDM_USER" -m 755 "$@"; }

# take the zorin-xp block out of the Prime hook (the rest stays as it was)
prime_unhook() {
    [ -n "$PRIME" ] && [ -f "$PRIME" ] && grep -qF "$BEGIN" "$PRIME" || return 0
    local tmp; tmp=$(mktemp)
    awk -v b="$BEGIN" -v e="$END" '$0 == b {skip=1} !skip {print} $0 == e {skip=0}' "$PRIME" > "$tmp"
    cat "$tmp" > "$PRIME"   # (keeps the owner and the permissions)
    rm -f "$tmp"
}


install_logon() {
    local src="$1" cursors="${2:-}"
    [ -f "$src/$UUID/extension.js" ] || { echo "Falta $src/$UUID (correr o build)." >&2; exit 1; }

    gdm_dir "$GDM_HOME/.local" "$GDM_HOME/.local/share" "$GDM_HOME/.local/share/gnome-shell" \
        "$GDM_HOME/.local/share/gnome-shell/extensions" "$GDM_HOME/.local/share/fonts" \
        "$GDM_HOME/.local/share/icons" "$GDM_HOME/.config" "$GDM_HOME/.config/fontconfig" "$FC" "$STATE"

    # previous values (each key only the first time it is changed)
    touch "$STATE/previous"
    for kv in org.gnome.shell:enabled-extensions \
              org.gnome.desktop.interface:cursor-theme org.gnome.desktop.interface:cursor-size \
              org.gnome.desktop.interface:font-hinting org.gnome.desktop.interface:font-antialiasing; do
        key=${kv#*:}
        grep -q "^$key=" "$STATE/previous" || echo "$key=$(gs get "${kv%%:*}" "$key")" >> "$STATE/previous"
    done

    rm -rf "$EXT" "$FONTS"
    cp -r "$src/$UUID" "$EXT"
    cp -r "$src/fonts" "$FONTS"
    for f in "${FC_FILES[@]}"; do cp "$src/$f" "$FC/$f"; done
    gdm_dir "$(dirname "$ENVD")"
    echo 'FREETYPE_PROPERTIES="truetype:interpreter-version=35"' > "$ENVD"
    prime_unhook
    rm -f "$SPLASH"
    if [ -n "$cursors" ] && [ -d "$cursors" ]; then
        rm -rf "$CURSORS"
        cp -r "$cursors" "$CURSORS"
        gdm_dir "$GDM_HOME/.icons"
        ln -sfn "../.local/share/icons/WindowsXP-Cursors" "$CURSORS_LINK"
        chown -h "$GDM_USER:$GDM_USER" "$CURSORS_LINK"
    fi
    chown -R "$GDM_USER:$GDM_USER" "$EXT" "$FONTS" "$FC" "$STATE" "$ENVD" \
        $( [ -d "$CURSORS" ] && echo "$CURSORS" )
    chmod -R u=rwX,go=rX "$EXT" "$FONTS"

    local cur
    cur=$(gs get org.gnome.shell enabled-extensions)
    gs set org.gnome.shell enabled-extensions "$(python3 -c '
import ast, sys
s = sys.argv[1].replace("@as ", "")
l = ast.literal_eval(s) if s.strip() else []
if sys.argv[2] not in l:
    l.append(sys.argv[2])
print(l)' "$cur" "$UUID")"
    if [ -d "$CURSORS" ]; then
        gs set org.gnome.desktop.interface cursor-theme 'WindowsXP-Cursors'
        gs set org.gnome.desktop.interface cursor-size 32
    fi
    gs set org.gnome.desktop.interface font-hinting 'full'
    gs set org.gnome.desktop.interface font-antialiasing 'grayscale'

    as_gdm fc-cache -f "$GDM_HOME/.local/share/fonts" >/dev/null 2>&1 || true
    echo "Ecrã de boas-vindas do XP instalado para o GDM (aparece no próximo início de sessão)."
}

remove_logon() {
    if [ -f "$STATE/previous" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                enabled-extensions) schema=org.gnome.shell ;;
                *) schema=org.gnome.desktop.interface ;;
            esac
            gs set "$schema" "$key" "$value" || gs reset "$schema" "$key"
        done < "$STATE/previous"
    else
        gs reset org.gnome.shell enabled-extensions || true
    fi
    prime_unhook
    rm -rf "$EXT" "$FONTS" "$CURSORS" "$STATE" "$ENVD" "$SPLASH"
    [ -L "$CURSORS_LINK" ] && rm -f "$CURSORS_LINK"
    for f in "${FC_FILES[@]}"; do rm -f "$FC/$f"; done
    as_gdm fc-cache -f >/dev/null 2>&1 || true
    echo "Ecrã de início de sessão reposto."
}

case "${1:-}" in
    install) install_logon "${2:?pasta build/logon}" "${3:-}" ;;
    remove) remove_logon ;;
    *) echo "Uso: sudo $0 install <build/logon> [<cursores>] | remove" >&2; exit 1 ;;
esac
