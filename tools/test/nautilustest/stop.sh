#!/bin/bash
# para o Nautilus de teste (só os processos do Broadway :7 e do dconf de teste)
for pid in $(pgrep -x nautilus); do
    tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -q '^BROADWAY_DISPLAY=:7$' && kill "$pid"
done
pkill -f '^gtk4-broadwayd :7' 2>/dev/null
true
