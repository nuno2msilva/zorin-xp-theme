#!/bin/bash
# Nautilus de teste: desenha numa página web (Broadway: http://127.0.0.1:8087),
# com o seu próprio D-Bus, uma cópia das definições do utilizador (dconf
# "zxptest") e os dados numa pasta à parte; a extensão é a de src/ (não a
# instalada). Nunca toca no Nautilus nem nas definições do utilizador.
#   run.sh [pasta]      stop.sh para parar
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
# definições: uma cópia das do utilizador em cada arranque
cp "$HOME/.config/dconf/user" "$HOME/.config/dconf/zxptest" 2>/dev/null
printf 'user-db:zxptest\n' > "$T/dconf-profile"
setsid gtk4-broadwayd :7 >"$T/broadway.log" 2>&1 &
sleep 1
setsid dbus-run-session -- env DCONF_PROFILE="$T/dconf-profile" GDK_BACKEND=broadway \
    BROADWAY_DISPLAY=:7 XDG_DATA_HOME="$T/data" NO_AT_BRIDGE=1 ZXP_TEST_RPC="$T/rpc" \
    nautilus --new-window "${1:-$HOME}" >"$T/nautilus.log" 2>&1 &
