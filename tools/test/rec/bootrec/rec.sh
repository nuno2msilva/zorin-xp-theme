#!/bin/bash
# Zorin XP — records the screen (KMS, at the graphics card level) during one boot.
# Installed by tools/test/rec/zxp-bootrec.sh; runs as a systemd service.
D=/var/tmp/zxp-bootrec
rm -f "$D/arm"
exec >"$D/rec.log" 2>&1
SECONDS_TOTAL=150
card=
while [ -z "$card" ]; do
    for c in /sys/class/drm/card[0-9]; do
        [ "$(basename "$(readlink -f "$c/device/driver")")" = i915 ] && card=/dev/dri/${c##*/}
    done
    [ -n "$card" ] || sleep 0.05
done
echo "placa $card às $(cut -d' ' -f1 /proc/uptime)"
sleep 0.3
n=0
while :; do
    up=$(cut -d' ' -f1 /proc/uptime)
    left=$(( SECONDS_TOTAL - ${up%.*} ))
    [ "$left" -gt 0 ] || break
    echo "seg $n início $up"
    LD_PRELOAD=$D/dropmaster.so LIBVA_DRIVER_NAME=i965 nice -n 10 ffmpeg -nostdin -loglevel error -y \
        -device "$card" -f kmsgrab -framerate 20 -i - \
        -vf 'hwmap=derive_device=vaapi,hwdownload,format=bgr0,scale=640:360,format=yuv420p' \
        -t "$left" -c:v libx264 -preset ultrafast -crf 26 "$D/seg-$(printf %03d $n)-$up.mkv"
    echo "seg $n fim $(cut -d' ' -f1 /proc/uptime) rc=$?"
    n=$((n + 1))
    sleep 0.1
done
echo fim
