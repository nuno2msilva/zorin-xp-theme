#!/bin/bash
# Test GNOME Shell for screenshots (README): a headless Zorin desktop session
# with the built theme (build/), FULLY isolated from the real session — own
# runtime dir, D-Bus, dconf, data and cache, and a fake home folder with the
# XP folders and a few sample files, so no personal file shows up. The fake
# home is seen as /home/utilizador (a private mount namespace: /home is
# replaced by an empty tmpfs only for this session, so the real home folder
# is not even visible to it).
#
#   python3 tools/build.py --out build            (the theme it uses)
#   SIZE=1280x800 WALLPAPER=<image> [X11=1] tools/test/shelltest/session.sh &
#   tools/test/shelltest/session.sh --app nautilus --new-window "/home/utilizador/Os meus documentos"
#   tools/test/shelltest/shot.sh out.png          (ev.sh/q.sh work as with run.sh)
#   tools/test/shelltest/session.sh --stop
#
# zorin-desktop-icons is enabled here, and when it starts it kills every
# desktop process started from the SYSTEM ding.js. The real session runs the
# copy in ~/.local/share/zorin-xp/ding; if it ever falls back to the system
# one, this would kill it — so in that case this refuses to start.
T="$(dirname "$(readlink -f "$0")")"; P="$(dirname "$(dirname "$(dirname "$T")")")"
E=${ZXP_TEST_ENV:-/tmp/zxp-session}
H="$E/home"                         # the fake home folder, on disk
HN=/home/utilizador                 # ...and where the session sees it

case "$1" in
--app)    # run an application inside the test session (spawned by the shell)
    shift
    args=$(printf '%s\n' "$@" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read().split("\n")[:-1]))')
    exec "$T/ev.sh" "imports.gi.GLib.spawn_async(null, $args, null, imports.gi.GLib.SpawnFlags.SEARCH_PATH, null) && 'ok'" ;;
--stop)
    pkill -f "wayland-display=wl-zx[p]"; sleep 1
    R=$(sed -n 's/^export .*XDG_RUNTIME_DIR=\([^ ]*\).*/\1/p' "$E/env.sh" 2>/dev/null)
    # (whatever the private bus started: identified by the private runtime dir)
    for p in /proc/[0-9]*; do
        tr '\0' '\n' 2>/dev/null < "$p/environ" | grep -qx "XDG_RUNTIME_DIR=$R" && kill "${p#/proc/}" 2>/dev/null
    done
    [ -n "$R" ] && { fusermount -u "$R/gvfs" 2>/dev/null; rm -rf "$R"; }
    exit 0 ;;
--ns1)    # as root of a new user namespace: the private mounts
    mkdir -p "$E/project"
    mount --bind "$P" "$E/project"            # (the project lives under /home)
    mount -t tmpfs tmpfs /home
    mkdir -p "$HN"
    mount --bind "$H" "$HN"
    # ...and back to the normal user for the session itself
    exec unshare -U --map-user="$ZXP_UID" --map-group="$ZXP_GID" -- "$E/project/tools/test/shelltest/session.sh" --ns2 ;;
--ns2)
    . "$E/env.sh"
    exec dbus-run-session -- "$0" --inner ;;
--inner)  # inside the private D-Bus session
    echo "$DBUS_SESSION_BUS_ADDRESS" > "$E/bus"
    g() { gsettings set "$@"; }
    g org.gnome.desktop.interface gtk-theme 'WindowsXP-Luna'
    g org.gnome.desktop.interface icon-theme 'WindowsXP'
    g org.gnome.desktop.interface color-scheme 'default'
    g org.gnome.desktop.interface font-name 'Tahoma 8.25'
    g org.gnome.desktop.interface document-font-name 'Tahoma 8.25'
    g org.gnome.desktop.interface monospace-font-name 'Lucida Console 9.75'
    g org.gnome.desktop.interface font-hinting 'full'
    g org.gnome.desktop.interface font-antialiasing 'grayscale'
    g org.gnome.desktop.interface overlay-scrolling false
    g org.gnome.desktop.interface clock-format '24h'
    g org.gnome.desktop.interface clock-show-date false
    g org.gnome.shell favorite-apps "[]"            # (XP had no pinned apps)
    g org.gnome.desktop.wm.preferences titlebar-font 'Trebuchet MS Bold 9.75'
    g org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'
    g org.gnome.mutter attach-modal-dialogs false
    g org.gnome.desktop.background picture-uri "file://$HN/.local/share/backgrounds/wallpaper"
    g org.gnome.desktop.background picture-options 'zoom'
    g org.gnome.nautilus.icon-view default-zoom-level 'small'
    g org.gnome.shell.extensions.user-theme name 'WindowsXP-Luna'
    g org.gnome.shell.extensions.zorin-desktop-icons show-home true
    g org.gnome.shell.extensions.zorin-desktop-icons show-trash true
    g org.gnome.shell.extensions.zorin-desktop-icons show-volumes false
    g org.gnome.shell.extensions.zorin-desktop-icons start-corner 'top-left'
    g org.gnome.shell disable-user-extensions false
    g org.gnome.shell enabled-extensions "['user-theme@gnome-shell-extensions.gcampax.github.com', 'zorin-taskbar@zorinos.com', 'zorin-menu@zorinos.com', 'zorin-xp@zorin-xp.local', 'zorin-xp-logon@zorin-xp.local', 'zorin-desktop-icons@zorinos.com']"
    python3 "$P/tools/setup/zorin_layout.py" >/dev/null
    # home folders with the XP names, like the folders component does
    ZXP_HOME="$HN" python3 "$P/tools/setup/xpfolders.py" apply >/dev/null
    DOCS="$HN/Os meus documentos"
    # (with some content: empty files are "application/x-zerosize", with a generic icon)
    for f in Relatório.docx Orçamento.xlsx Apresentação.pptx; do printf 'PK\003\004' > "$DOCS/$f"; done
    printf 'Lista de compras\n' > "$DOCS/Notas.txt"
    for w in "Alentejo.bmp" "Azul.jpg" "Cristal.jpg" "Flor de lua.jpg"; do
        cp "$P/windows/xp-pro-pt/Web/Wallpaper/$w" "$DOCS/As minhas imagens/" 2>/dev/null
    done
    # "Os meus documentos" on the desktop: a trusted launcher (as on the real desktop)
    L="$HN/Ambiente de trabalho/Os meus documentos.desktop"
    printf '[Desktop Entry]\nType=Application\nName=Os meus documentos\nIcon=folder-documents\nExec=nautilus --new-window "%s"\nTerminal=false\n' "$DOCS" > "$L"
    chmod +x "$L"; gio set "$L" metadata::trusted true
    # (services the bus starts — file-roller, nautilus... — open their windows here)
    WAYLAND_DISPLAY=wl-zxp GDK_BACKEND=wayland dbus-update-activation-environment WAYLAND_DISPLAY GDK_BACKEND \
        HOME XDG_CONFIG_HOME XDG_DATA_HOME XDG_CACHE_HOME XDG_RUNTIME_DIR XDG_CURRENT_DESKTOP FREETYPE_PROPERTIES
    # (X11=1: with Xwayland, for X11 clients — e.g. Plymouth's x11 renderer)
    NOX11=--no-x11; [ -n "$X11" ] && NOX11=
    exec gnome-shell --headless --wayland $NOX11 --virtual-monitor "${SIZE:-1280x800}" --mode=zorin --wayland-display=wl-zxp ;;
esac

# --- safety: never start if a real desktop process runs from the system path
for f in /proc/[0-9]*/cmdline; do
    if tr '\0' ' ' 2>/dev/null < "$f" | grep -q "^gjs /usr/share/gnome-shell/extensions/zorin-desktop-icons@zorinos.com/app/ding.js"; then
        echo "A real desktop icons process runs from the system path ($f): not starting." >&2
        exit 1
    fi
done
[ -d "$P/build/shell/WindowsXP-Luna" ] || { echo "No build/: python3 tools/build.py --out build" >&2; exit 1; }

# --- the fake home folder, with the built theme installed into it (paths
#     written into files use $HN, where the session sees it)
rm -rf "$E"; mkdir -p "$E"
R=$(mktemp -d /tmp/zxp-run.XXXX); chmod 700 "$R"
D="$H/.local/share"; C="$H/.config"; DN="$HN/.local/share"
mkdir -p "$H"/{Documentos,Imagens,Música,Vídeos,Secretária,Transferências,Modelos,Público} \
    "$C"/{fontconfig/conf.d,gtk-3.0,gtk-4.0} "$D"/{gnome-shell/extensions,icons,fonts,backgrounds,nautilus-python/extensions,zorin-xp/gettext,dbus-1/services} "$H/.themes" "$H/.cache"
cat > "$C/user-dirs.dirs" <<'DIRS'
XDG_DESKTOP_DIR="$HOME/Secretária"
XDG_DOWNLOAD_DIR="$HOME/Transferências"
XDG_TEMPLATES_DIR="$HOME/Modelos"
XDG_PUBLICSHARE_DIR="$HOME/Público"
XDG_DOCUMENTS_DIR="$HOME/Documentos"
XDG_MUSIC_DIR="$HOME/Música"
XDG_PICTURES_DIR="$HOME/Imagens"
XDG_VIDEOS_DIR="$HOME/Vídeos"
DIRS
cp -a "$P/build/gtk/WindowsXP-Luna" "$H/.themes/"
cp -a "$P/build/shell/WindowsXP-Luna/gnome-shell" "$H/.themes/WindowsXP-Luna/"
cp -a "$P/build/icons/WindowsXP" "$D/icons/"
cp -a "$P/build/fonts/WindowsXP" "$D/fonts/"
cp "$P/build/fonts/"*.conf "$C/fontconfig/conf.d/"
cp -a "$P/build/extension/zorin-xp@zorin-xp.local" "$D/gnome-shell/extensions/"
# (the logon extension too: with ZXP_LOGON_TEST it allows Eval over D-Bus)
cp -a "$P/build/logon/zorin-xp-logon@zorin-xp.local" "$D/gnome-shell/extensions/"
cp "$P/src/nautilus-xp/zorin_xp_explorer.py" "$D/nautilus-python/extensions/"
cat "$P/src/desktop/gtk3-desktop-labels.css" > "$C/gtk-3.0/gtk.css"
printf '@import url("file://%s/.themes/WindowsXP-Luna/gtk-4.0/gtk.css");\n' "$HN" > "$C/gtk-4.0/gtk.css"
cp "${WALLPAPER:-$P/windows/xp-pro-pt/Web/Wallpaper/Alentejo.bmp}" "$D/backgrounds/wallpaper"
# the XP grid copy of the desktop icons program, and "O meu computador"/"Reciclagem"
python3 "$P/tools/setup/dingcopy.py" "$D/zorin-xp/ding" >/dev/null
python3 "$P/tools/setup/molocale.py" "$D/zorin-xp/locale" >/dev/null
cc -O2 -shared -fPIC -o "$D/zorin-xp/gettext/zorin-xp-gettext.so" "$P/src/gettext-shim/zorin-xp-gettext.c" -ldl
# Files started by the bus with the XP names too (as the folders component does)
for svc in org.gnome.Nautilus org.freedesktop.FileManager1; do
    printf '[D-BUS Service]\nName=%s\nExec=/usr/bin/env LD_PRELOAD=%s ZXP_LOCALEDIR=%s ZXP_GETTEXT_DOMAINS=nautilus /usr/bin/nautilus --gapplication-service\n' \
        "$svc" "$DN/zorin-xp/gettext/zorin-xp-gettext.so" "$DN/zorin-xp/locale" > "$D/dbus-1/services/$svc.service"
done

# --- environment inside the session
cat > "$E/env.sh" <<ENV
unset XDG_SESSION_ID XDG_SEAT XDG_VTNR XDG_SESSION_TYPE XDG_SESSION_CLASS XDG_SESSION_DESKTOP DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS
export HOME="$HN" XDG_CONFIG_HOME="$HN/.config" XDG_DATA_HOME="$DN" XDG_CACHE_HOME="$HN/.cache" XDG_RUNTIME_DIR=$R
export XDG_CURRENT_DESKTOP=zorin:GNOME FREETYPE_PROPERTIES="truetype:interpreter-version=35" ZXP_LOGON_TEST=1
ENV
echo "$E" > /tmp/zxp-shelltest.env
ZXP_UID=$(id -u) ZXP_GID=$(id -g) exec unshare -r -m --propagation private -- "$0" --ns1
