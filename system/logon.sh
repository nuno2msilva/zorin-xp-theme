#!/usr/bin/env bash
# Zorin XP — ecrã de boas-vindas do XP no ecrã de início de sessão (GDM).
#
# O ecrã de início de sessão corre como o utilizador "gdm", por isso isto
# precisa de root. Não mexe em /usr; quase tudo fica na pasta do utilizador
# gdm (/var/lib/gdm3), como se fosse a configuração pessoal dele:
#   .local/share/gnome-shell/extensions/zorin-xp-logon@zorin-xp.local
#   .local/share/fonts/zorin-xp           (Tahoma e Arial do XP)
#   .config/fontconfig/conf.d/6x-*.conf   (nitidez dos tipos de letra do XP)
#   .local/share/icons/WindowsXP-Cursors  (cursores do XP, se instalados)
#   .icons/WindowsXP-Cursors              (ligação: o Xcursor só procura aí)
#   .config/environment.d/60-zorin-xp-freetype.conf (interpretador v35)
#   dconf do gdm: enabled-extensions, cursor-theme, cursor-size, font-hinting,
#                 font-antialiasing
# Os valores anteriores ficam em .local/share/zorin-xp-logon/previous.
# (Uma versão anterior punha um bloco marcado em /etc/gdm3/Prime/Default;
# o install e o remove tiram-no se lá estiver.)
#
# Uso:  sudo system/logon.sh install <build/logon> [<pasta dos cursores XP>]
#       sudo system/logon.sh remove
# Tem efeito na próxima vez que o ecrã de início de sessão aparecer.
#
# Emergência (o ecrã não deixa entrar): Ctrl+Alt+F3, entrar no terminal e
#   sudo <pasta do projeto>/system/logon.sh remove && sudo systemctl restart gdm3
set -euo pipefail

UUID=zorin-xp-logon@zorin-xp.local
if [ -n "${ZXP_TEST_HOME:-}" ]; then
    # ensaio sem root: uma pasta qualquer faz de pasta do gdm
    GDM_USER=$(id -un); GDM_HOME=$ZXP_TEST_HOME
elif getent passwd gdm >/dev/null; then GDM_USER=gdm; else GDM_USER=Debian-gdm; fi
GDM_HOME=${GDM_HOME:-$(getent passwd "$GDM_USER" | cut -d: -f6)}
STATE=$GDM_HOME/.local/share/zorin-xp-logon
EXT=$GDM_HOME/.local/share/gnome-shell/extensions/$UUID
FONTS=$GDM_HOME/.local/share/fonts/zorin-xp
FC=$GDM_HOME/.config/fontconfig/conf.d
CURSORS=$GDM_HOME/.local/share/icons/WindowsXP-Cursors
# (o Xcursor — que dá os cursores ao ecrã de início de sessão — só procura
# em ~/.icons e /usr/share/icons: sem esta ligação ficavam os do sistema)
CURSORS_LINK=$GDM_HOME/.icons/WindowsXP-Cursors
FC_FILES=(60-windows-xp.conf 61-windows-xp-arial.conf)
# interpretador TrueType do XP (traços encaixados no píxel, como o GDI)
ENVD=$GDM_HOME/.config/environment.d/60-zorin-xp-freetype.conf
SPLASH=$GDM_HOME/.local/bin/zorin-xp-splash
PRIME=${ZXP_TEST_PRIME:-/etc/gdm3/Prime/Default}
[ -n "${ZXP_TEST_HOME:-}" ] && [ -z "${ZXP_TEST_PRIME:-}" ] && PRIME=
BEGIN='# >>> zorin-xp: ecrã do XP enquanto o greeter arranca (system/logon.sh)'
END='# <<< zorin-xp'

[ "$(id -u)" -eq 0 ] || [ -n "${ZXP_TEST_HOME:-}" ] || { echo "Correr com sudo." >&2; exit 1; }
[ -d "$GDM_HOME" ] || { echo "Utilizador do GDM não encontrado." >&2; exit 1; }

as_gdm() {  # como o próprio GDM faz (/usr/share/gdm/generate-config)
    if [ -n "${ZXP_TEST_HOME:-}" ]; then
        env -i PATH=/usr/bin:/bin HOME="$GDM_HOME" XDG_CONFIG_HOME="$GDM_HOME/.config" \
            XDG_DATA_HOME="$GDM_HOME/.local/share" XDG_CACHE_HOME="$GDM_HOME/.cache" "$@"
        return
    fi
    setpriv --reuid "$GDM_USER" --regid "$GDM_USER" --init-groups --reset-env \
        env HOME="$GDM_HOME" "$@"
}
gs() { as_gdm dbus-run-session -- gsettings "$@"; }
gdm_dir() { install -d -o "$GDM_USER" -g "$GDM_USER" -m 755 "$@"; }

# tira o bloco do zorin-xp do gancho Prime (fica o resto como estava)
prime_unhook() {
    [ -n "$PRIME" ] && [ -f "$PRIME" ] && grep -qF "$BEGIN" "$PRIME" || return 0
    local tmp; tmp=$(mktemp)
    awk -v b="$BEGIN" -v e="$END" '$0 == b {skip=1} !skip {print} $0 == e {skip=0}' "$PRIME" > "$tmp"
    cat "$tmp" > "$PRIME"   # (mantém o dono e as permissões)
    rm -f "$tmp"
}


install_logon() {
    local src="$1" cursors="${2:-}"
    [ -f "$src/$UUID/extension.js" ] || { echo "Falta $src/$UUID (correr o build)." >&2; exit 1; }

    gdm_dir "$GDM_HOME/.local" "$GDM_HOME/.local/share" "$GDM_HOME/.local/share/gnome-shell" \
        "$GDM_HOME/.local/share/gnome-shell/extensions" "$GDM_HOME/.local/share/fonts" \
        "$GDM_HOME/.local/share/icons" "$GDM_HOME/.config" "$GDM_HOME/.config/fontconfig" "$FC" "$STATE"

    # valores anteriores (cada chave só da primeira vez que é alterada)
    touch "$STATE/previous"
    for kv in org.gnome.shell:enabled-extensions \
              org.gnome.desktop.interface:cursor-theme org.gnome.desktop.interface:cursor-size \
              org.gnome.desktop.interface:font-hinting org.gnome.desktop.interface:font-antialiasing; do
        key=${kv#*:}
        grep -q "^$key=" "$STATE/previous" || echo "$key=$(gs get "${kv%%:*}" "$key")" >> "$STATE/previous"
    done

    rm -rf "$EXT" "$FONTS"
    cp -r "$src/$UUID" "$EXT"
    cp -r "$src/fonts" "$FONTS"
    for f in "${FC_FILES[@]}"; do cp "$src/$f" "$FC/$f"; done
    gdm_dir "$(dirname "$ENVD")"
    echo 'FREETYPE_PROPERTIES="truetype:interpreter-version=35"' > "$ENVD"
    prime_unhook
    rm -f "$SPLASH"
    if [ -n "$cursors" ] && [ -d "$cursors" ]; then
        rm -rf "$CURSORS"
        cp -r "$cursors" "$CURSORS"
        gdm_dir "$GDM_HOME/.icons"
        ln -sfn "../.local/share/icons/WindowsXP-Cursors" "$CURSORS_LINK"
        chown -h "$GDM_USER:$GDM_USER" "$CURSORS_LINK"
    fi
    chown -R "$GDM_USER:$GDM_USER" "$EXT" "$FONTS" "$FC" "$STATE" "$ENVD" \
        $( [ -d "$CURSORS" ] && echo "$CURSORS" )
    chmod -R u=rwX,go=rX "$EXT" "$FONTS"

    local cur
    cur=$(gs get org.gnome.shell enabled-extensions)
    gs set org.gnome.shell enabled-extensions "$(python3 -c '
import ast, sys
s = sys.argv[1].replace("@as ", "")
l = ast.literal_eval(s) if s.strip() else []
if sys.argv[2] not in l:
    l.append(sys.argv[2])
print(l)' "$cur" "$UUID")"
    if [ -d "$CURSORS" ]; then
        gs set org.gnome.desktop.interface cursor-theme 'WindowsXP-Cursors'
        gs set org.gnome.desktop.interface cursor-size 32
    fi
    gs set org.gnome.desktop.interface font-hinting 'full'
    gs set org.gnome.desktop.interface font-antialiasing 'grayscale'

    as_gdm fc-cache -f "$GDM_HOME/.local/share/fonts" >/dev/null 2>&1 || true
    echo "Ecrã de boas-vindas do XP instalado para o GDM (aparece no próximo início de sessão)."
}

remove_logon() {
    if [ -f "$STATE/previous" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                enabled-extensions) schema=org.gnome.shell ;;
                *) schema=org.gnome.desktop.interface ;;
            esac
            gs set "$schema" "$key" "$value" || gs reset "$schema" "$key"
        done < "$STATE/previous"
    else
        gs reset org.gnome.shell enabled-extensions || true
    fi
    prime_unhook
    rm -rf "$EXT" "$FONTS" "$CURSORS" "$STATE" "$ENVD" "$SPLASH"
    [ -L "$CURSORS_LINK" ] && rm -f "$CURSORS_LINK"
    for f in "${FC_FILES[@]}"; do rm -f "$FC/$f"; done
    as_gdm fc-cache -f >/dev/null 2>&1 || true
    echo "Ecrã de início de sessão reposto."
}

case "${1:-}" in
    install) install_logon "${2:?pasta build/logon}" "${3:-}" ;;
    remove) remove_logon ;;
    *) echo "Uso: sudo $0 install <build/logon> [<cursores>] | remove" >&2; exit 1 ;;
esac
