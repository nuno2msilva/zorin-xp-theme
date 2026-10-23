#!/bin/bash
# rebuilds the IE theme, puts it in the test profile, restarts the test Zen
# and takes a capture: ./iter.sh out.png [url]
D="$(dirname "$(readlink -f "$0")")"; P="$(dirname "$(dirname "$(dirname "$D")")")"
T="$HOME/.var/app/app.zen_browser.zen/zxp-test-profile"
"$D/stop.sh"; sleep 2
# (a session with popup windows blocks Marionette's start)
rm -rf "$T/sessionstore.jsonlz4" "$T"/zen-sessions*.jsonlz4 "$T/sessionstore-backups"
python3 "$P/tools/build.py" --out "$P/build" zen >/dev/null || exit 1
rm -rf "$T/chrome/zorin-xp-ie"; cp -r "$P/build/zen/zorin-xp-ie" "$T/chrome/"
printf '@import url("zorin-xp-ie/ie.css");\n' > "$T/chrome/userChrome.css"
printf '@import url("zorin-xp-ie/content.css");\n' > "$T/chrome/userContent.css"
(MOZ_HEADLESS_WIDTH=1911 MOZ_HEADLESS_HEIGHT=903 setsid "$D/run.sh" > /tmp/zxp-zentest.log 2>&1 &)
sleep 2; for i in $(seq 1 40); do (echo > /dev/tcp/127.0.0.1/2829) 2>/dev/null && break; sleep 1; done; sleep 4
python3 "$D/mn.py" size 1911 903 >/dev/null
[ -n "$2" ] && { python3 "$D/mn.py" go "$2"; sleep 6; }
sleep 1; python3 "$D/mn.py" shot "$1"
