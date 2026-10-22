#!/bin/bash
# fecha só o Zen de teste (perfil zxp-test-profile): pelo nome do programa,
# para não apanhar shells cuja linha de comando contenha o mesmo texto
for p in $(pgrep -f "zxp-test-profile"); do
    exe=$(tr '\0' '\n' < /proc/$p/cmdline 2>/dev/null | head -1)
    case "$(basename "$exe")" in zen|zen-bin|flatpak) kill "$p";; esac
done
