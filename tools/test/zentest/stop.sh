#!/bin/bash
# closes only the test Zen (zxp-test-profile profile): by program name, so
# that shells whose command line contains the same text are not caught
for p in $(pgrep -f "zxp-test-profile"); do
    exe=$(tr '\0' '\n' < /proc/$p/cmdline 2>/dev/null | head -1)
    case "$(basename "$exe")" in zen|zen-bin|flatpak) kill "$p";; esac
done
