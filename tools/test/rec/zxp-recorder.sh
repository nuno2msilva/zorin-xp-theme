#!/bin/bash
# Grava o ecrã que estiver ativo — a sessão OU o ecrã de início de sessão do
# GDM (outro servidor X, do utilizador gdm) — com o cursor, mudando de servidor
# quando se termina sessão / entra. Corre como root fora da sessão
# (systemd-run), por isso sobrevive a terminar sessão.
# Uso: zxp-recorder.sh <pasta> [segundos máx]   Parar: touch /tmp/zxp-rec.stop
OUT="$1"; MAX="${2:-1200}"; STOP=/tmp/zxp-rec.stop
mkdir -p "$OUT"; rm -f "$STOP"; start=$(date +%s); n=0
log() { echo "$(date +%T) $*" >> "$OUT/recorder.log"; }

active_x() {  # imprime "display auth" do Xorg do VT ativo
    local vt pid args auth disp
    vt=$(cat /sys/class/tty/tty0/active); vt=${vt#tty}
    for pid in $(pgrep -x Xorg); do
        args=$(tr '\0' ' ' < /proc/$pid/cmdline)
        case " $args " in *" vt$vt "*) ;; *) continue ;; esac
        auth=$(echo "$args" | grep -oE '\-auth [^ ]+' | cut -d' ' -f2)
        disp=$(ss -xlpH 2>/dev/null | grep "pid=$pid," | grep -oE '/tmp/\.X11-unix/X[0-9]+' | head -1)
        [ -n "$disp" ] && { echo ":${disp##*X} $auth"; return; }
    done
}

while [ ! -e "$STOP" ] && [ $(( $(date +%s) - start )) -lt "$MAX" ]; do
    read -r disp auth <<< "$(active_x)"
    if [ -z "$disp" ]; then sleep 0.3; continue; fi
    vt=$(cat /sys/class/tty/tty0/active)
    n=$((n + 1)); seg="$OUT/seg$(printf %02d $n).mp4"
    log "segmento $n: $vt $disp"
    XAUTHORITY="$auth" ffmpeg -loglevel error -y -f x11grab -draw_mouse 1 -framerate 20 -i "$disp" \
        -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p "$seg" 2>>"$OUT/recorder.log" &
    fp=$!
    while kill -0 $fp 2>/dev/null; do
        [ -e "$STOP" ] && break
        [ "$(cat /sys/class/tty/tty0/active)" != "$vt" ] && break
        sleep 0.3
    done
    kill -INT $fp 2>/dev/null; wait $fp 2>/dev/null
done
log "fim"
chown -R 1000:1000 "$OUT"; rm -f "$STOP"
