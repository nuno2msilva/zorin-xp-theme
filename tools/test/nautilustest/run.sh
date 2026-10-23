#!/bin/bash
# Test Nautilus: draws into a web page (Broadway: http://127.0.0.1:8087),
# with its own D-Bus, a copy of the user's settings (dconf "zxptest") and the
# data in a separate folder; the extension is the one in src/ (not the
# installed one). It never touches the user's Nautilus or settings.
#   run.sh [folder]      stop.sh to stop
D="$(dirname "$(readlink -f "$0")")"; P="$(dirname "$(dirname "$(dirname "$D")")")"
T="$HOME/.cache/zorin-xp/nautilustest"
"$D/stop.sh" 2>/dev/null
rm -rf "$T/data" "$T/rpc"
mkdir -p "$T/data/nautilus-python/extensions" "$HOME/.config/dconf"
ln -s "$P/src/nautilus-xp/zorin_xp_explorer.py" "$T/data/nautilus-python/extensions/"
ln -s "$D/zxp_test_hook.py" "$T/data/nautilus-python/extensions/"
for x in icons fonts sounds themes recently-used.xbel; do
    [ -e "$HOME/.local/share/$x" ] && ln -s "$HOME/.local/share/$x" "$T/data/$x"
done
# settings: a copy of the user's on every start
cp "$HOME/.config/dconf/user" "$HOME/.config/dconf/zxptest" 2>/dev/null
printf 'user-db:zxptest\n' > "$T/dconf-profile"
# ZXP_WAYLAND=<socket path>: draws into a headless GNOME Shell instead (e.g.
# MODE=user tools/test/shelltest/run.sh), where GTK gets real frames — Broadway
# only lays out and draws while a visible browser shows its page
# ZXP_X11=<display>: on X11 instead, as the real session (e.g. a rootful
# Xwayland inside that headless Shell: WAYLAND_DISPLAY=<socket> Xwayland :77
# -geometry 1920x1080) — never the real display
if [ -n "$ZXP_X11" ]; then
    BACKEND="GDK_BACKEND=x11 DISPLAY=$ZXP_X11"
elif [ -n "$ZXP_WAYLAND" ]; then
    BACKEND="GDK_BACKEND=wayland WAYLAND_DISPLAY=$ZXP_WAYLAND"
else
    setsid gtk4-broadwayd :7 >"$T/broadway.log" 2>&1 &
    sleep 1
    BACKEND="GDK_BACKEND=broadway"
fi
# (BROADWAY_DISPLAY also marks the test Nautilus for stop.sh)
setsid dbus-run-session -- env DCONF_PROFILE="$T/dconf-profile" $BACKEND \
    BROADWAY_DISPLAY=:7 XDG_DATA_HOME="$T/data" NO_AT_BRIDGE=1 ZXP_TEST_RPC="$T/rpc" \
    nautilus --new-window "${1:-$HOME}" >"$T/nautilus.log" 2>&1 &
