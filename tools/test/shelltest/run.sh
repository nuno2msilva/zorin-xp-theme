#!/bin/bash
# Test GNOME Shell, headless, in gdm mode, FULLY isolated from the real
# session: no XDG_SESSION_ID/seat/display (gdm mode talks to logind about the
# inherited session — it once made the real session lock/crash), its own
# runtime dir, dconf, data and cache. Usage: SIZE=1920x1080 ./run.sh &
T="$(dirname "$(readlink -f "$0")")"; P="$(dirname "$(dirname "$(dirname "$T")")")"
E=${ZXP_TEST_ENV:-/tmp/zxp-shelltest}; rm -rf "$E"; mkdir -p "$E"/{data/gnome-shell/extensions,data/fonts,cfg/fontconfig/conf.d,cache}
R=$(mktemp -d /tmp/zxp-run.XXXX); chmod 700 "$R"
cp -a "$P/build/logon/zorin-xp-logon@zorin-xp.local" "$E/data/gnome-shell/extensions/"
cp "$P/build/logon/fonts/"* "$P/build/fonts/WindowsXP/"* "$E/data/fonts/" 2>/dev/null
cp "$P/build/logon/"*.conf "$E/cfg/fontconfig/conf.d/"
unset XDG_SESSION_ID XDG_SEAT XDG_VTNR XDG_SESSION_TYPE XDG_SESSION_CLASS XDG_SESSION_DESKTOP DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS
export XDG_CONFIG_HOME=$E/cfg XDG_DATA_HOME=$E/data XDG_CACHE_HOME=$E/cache XDG_RUNTIME_DIR=$R
export GDM_GREETER_TEST=1 ZXP_LOGON_TEST=1 FREETYPE_PROPERTIES="truetype:interpreter-version=35"
echo "$E" > /tmp/zxp-shelltest.env
exec dbus-run-session -- bash -c '
  echo "$DBUS_SESSION_BUS_ADDRESS" > '"$E"'/bus
  gsettings set org.gnome.desktop.interface font-hinting full
  gsettings set org.gnome.shell enabled-extensions "[\"zorin-xp-logon@zorin-xp.local\"]"
  exec gnome-shell --headless --wayland --no-x11 --virtual-monitor '"${SIZE:-1920x1080}"' --mode=${MODE:-gdm} --wayland-display=wl-zxp
'
