#!/bin/bash
# Zorin XP — grava o ecrã no próximo arranque (diagnóstico, uma vez só).
# Uso: sudo tools/test/rec/zxp-bootrec.sh install | remove
set -euo pipefail
H="$(dirname "$(readlink -f "$0")")/bootrec"
D=/var/tmp/zxp-bootrec
U=/etc/systemd/system/zxp-bootrec.service
case "${1:-}" in
install)
    rm -rf "$D"; install -d -m 755 "$D"
    gcc -O2 -shared -fPIC -o "$D/dropmaster.so" "$H/dropmaster.c" -ldl
    install -m 755 "$H/rec.sh" "$D/rec.sh"
    install -m 644 "$H/zxp-bootrec.service" "$U"
    systemctl daemon-reload
    systemctl enable zxp-bootrec.service
    touch "$D/arm"
    echo "Gravação armada para o próximo arranque (150 s)." ;;
remove)
    systemctl disable zxp-bootrec.service 2>/dev/null || true
    rm -f "$U"; systemctl daemon-reload
    rm -rf "$D"
    echo "Gravação do arranque removida." ;;
*) echo "Uso: sudo $0 install | remove" >&2; exit 1 ;;
esac
