#!/usr/bin/env bash
# Corre um comando com o tema gerado em build/ sem o instalar no sistema:
# tema GTK, tipos de letra e regras do fontconfig ficam isolados neste processo.
# Uso: tools/test/preview.sh <comando> [args...]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
SANDBOX="$HERE/build/.preview"
mkdir -p "$SANDBOX/themes"
ln -sfn "$HERE/build/gtk/WindowsXP-Luna" "$SANDBOX/themes/WindowsXP-Luna"
cat > "$SANDBOX/fonts.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>$HERE/build/fonts/WindowsXP</dir>
  <include ignore_missing="yes">$HERE/build/fonts/60-windows-xp.conf</include>
  <cachedir>$SANDBOX/fontcache</cachedir>
</fontconfig>
EOF
export FONTCONFIG_FILE="$SANDBOX/fonts.conf"
export XDG_DATA_HOME="$SANDBOX"
export GTK_THEME="WindowsXP-Luna"
export GTK_OVERLAY_SCROLLING=0
export FREETYPE_PROPERTIES="truetype:interpreter-version=35"
exec "$@"
