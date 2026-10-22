#!/usr/bin/env bash
# Zorin XP — instalador.
# Uso: ./install.sh [componentes...]
# Constrói o tema a partir de assets/ (os recursos do XP já extraídos: para
# os extrair de novo de uma cópia do Windows, tools/extract.py) e instala-o.
# Componentes: sounds cursors fonts gtk shell extension icons folders explorer filechooser zen logon boot
#   (por omissão: todos; logon (ecrã de início de sessão) e boot (ecrã de
#   arranque, Plymouth) pedem a palavra-passe de administrador)
# Tudo é copiado (para a home e, com sudo, para as pastas do sistema): nada
# fica a depender desta pasta. O que é instalado fica registado em
# ~/.local/share/zorin-xp/installed-files.txt; rescue/restore.sh (também
# copiado para ~/.local/share/zorin-xp/uninstall) remove-o e repõe as
# definições originais.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
COMPONENTS=()
while [ $# -gt 0 ]; do
    case "$1" in
        *) COMPONENTS+=("$1"); shift ;;
    esac
done
[ ${#COMPONENTS[@]} -eq 0 ] && COMPONENTS=(sounds cursors fonts gtk shell extension icons folders explorer filechooser zen logon boot)

STATE_DIR="$HOME/.local/share/zorin-xp"
MANIFEST="$STATE_DIR/installed-files.txt"
BUILD="$HERE/build"
mkdir -p "$STATE_DIR"
touch "$MANIFEST"

# Snapshot original antes da primeira alteração
if [ ! -e "$STATE_DIR/backup/original" ]; then
    "$HERE/rescue/backup.sh"
fi

# Desinstalador autónomo: o restore.sh e os ajudantes que ele chama, nas
# mesmas pastas relativas, para se poder reverter mesmo depois de apagar esta
# pasta (nada do que é instalado depende dela)
UNINSTALL="$STATE_DIR/uninstall"
rm -rf "$UNINSTALL"
for f in rescue/restore.sh src/fontconfig/zorin-xp-browser-fonts \
         tools/setup/explorerprefs.py tools/setup/zenprefs.py tools/setup/xpfolders.py \
         system/logon.sh system/bootscreen.sh; do
    install -D -m "$(stat -c %a "$HERE/$f")" "$HERE/$f" "$UNINSTALL/$f"
done

record() {  # regista um caminho instalado (uma vez)
    grep -qxF "$1" "$MANIFEST" || echo "$1" >> "$MANIFEST"
}

install_dir() {  # install_dir <origem> <destino>
    rm -rf -- "$2"
    mkdir -p "$(dirname "$2")"
    cp -a "$1" "$2"
    record "$2"
}

install_file() {  # install_file <origem> <destino>
    mkdir -p "$(dirname "$2")"
    cp -a "$1" "$2"
    record "$2"
}

zen_profile() {  # pasta do perfil por omissão do Zen (Flatpak), ou nada
    local zen="$HOME/.var/app/app.zen_browser.zen/.zen" prof=""
    [ -f "$zen/profiles.ini" ] &&
        prof=$(awk -F= '/^\[Install/{i=1;next} /^\[/{i=0} i&&$1=="Default"{print $2; exit}' "$zen/profiles.ini")
    [ -n "$prof" ] && [ -d "$zen/$prof" ] && echo "$zen/$prof"
}

echo "A construir o tema a partir de: $HERE/assets"
python3 "$HERE/tools/build.py" --out "$BUILD" "${COMPONENTS[@]}"

for c in "${COMPONENTS[@]}"; do
    case "$c" in
    sounds)
        install_dir "$BUILD/sounds/WindowsXP" "$HOME/.local/share/sounds/WindowsXP"
        # (o clique ao mudar de pasta no Ficheiros: extensão do Shell, navigationSound.js)
        gsettings set org.gnome.desktop.sound theme-name 'WindowsXP'
        gsettings set org.gnome.desktop.sound event-sounds true
        ;;
    cursors)
        install_dir "$BUILD/cursors/WindowsXP" "$HOME/.local/share/icons/WindowsXP-Cursors"
        # o Xcursor (os cursores das aplicações em X11) só procura em ~/.icons
        # e /usr/share/icons: sem esta ligação as aplicações não encontravam o
        # tema e ficavam com os cursores de reserva (pretos, sem os do XP)
        if [ ! -e "$HOME/.icons/WindowsXP-Cursors" ] || [ -L "$HOME/.icons/WindowsXP-Cursors" ]; then
            mkdir -p "$HOME/.icons"
            ln -sfn "$HOME/.local/share/icons/WindowsXP-Cursors" "$HOME/.icons/WindowsXP-Cursors"
            record "$HOME/.icons/WindowsXP-Cursors"
        fi
        gsettings set org.gnome.desktop.interface cursor-theme 'WindowsXP-Cursors'
        gsettings set org.gnome.desktop.interface cursor-size 32
        # aplicações que não leem o gsettings (X11 puro, Qt, Java, Wine): o tema
        # "default" do Xcursor e as variáveis XCURSOR_* (ativas após novo login)
        if [ ! -e "$HOME/.icons/default/index.theme" ]; then
            mkdir -p "$HOME/.icons/default"
            printf '[Icon Theme]\nName=Default\nInherits=WindowsXP-Cursors\n' \
                > "$HOME/.icons/default/index.theme"
            record "$HOME/.icons/default"
        fi
        mkdir -p "$HOME/.config/environment.d"
        printf 'XCURSOR_THEME=WindowsXP-Cursors\nXCURSOR_SIZE=32\n' \
            > "$HOME/.config/environment.d/60-zorin-xp-cursor.conf"
        record "$HOME/.config/environment.d/60-zorin-xp-cursor.conf"
        # Flatpak: as aplicações só veem os temas da pasta pessoal com permissão
        # (só se ainda não houver definições globais do utilizador — não mexer nelas)
        if command -v flatpak >/dev/null && [ ! -e "$HOME/.local/share/flatpak/overrides/global" ]; then
            flatpak override --user --filesystem=xdg-data/icons:ro --filesystem=~/.icons:ro \
                --env=XCURSOR_THEME=WindowsXP-Cursors --env=XCURSOR_SIZE=32
            record "$HOME/.local/share/flatpak/overrides/global"
        fi
        ;;
    fonts)
        install_dir "$BUILD/fonts/WindowsXP" "$HOME/.local/share/fonts/WindowsXP"
        install_file "$BUILD/fonts/60-windows-xp.conf" "$HOME/.config/fontconfig/conf.d/60-windows-xp.conf"
        install_file "$BUILD/fonts/61-windows-xp-arial.conf" "$HOME/.config/fontconfig/conf.d/61-windows-xp-arial.conf"
        install_file "$BUILD/fonts/62-windows-xp-prefer.conf" "$HOME/.config/fontconfig/conf.d/62-windows-xp-prefer.conf"
        # Interpretador TrueType v35 (hinting horizontal, como o GDI do XP); ativo após novo login
        mkdir -p "$HOME/.config/environment.d"
        echo 'FREETYPE_PROPERTIES="truetype:interpreter-version=35"' \
            > "$HOME/.config/environment.d/60-zorin-xp-freetype.conf"
        record "$HOME/.config/environment.d/60-zorin-xp-freetype.conf"
        # ...mas os motores de browser (Electron/Chromium, Firefox) posicionam as
        # letras em frações de píxel e com o v35 o espaçamento fica irregular:
        # essas aplicações ficam com o interpretador normal (voltar a correr o
        # comando depois de instalar aplicações novas)
        install_file "$HERE/src/fontconfig/zorin-xp-browser-fonts" "$HOME/.local/bin/zorin-xp-browser-fonts"
        "$HOME/.local/bin/zorin-xp-browser-fonts"
        fc-cache -f "$HOME/.local/share/fonts" >/dev/null
        # Tamanhos em px inteiros como no XP a 96 ppp: 8 pt = 11 px, 10 pt = 13 px
        gsettings set org.gnome.desktop.interface font-name 'Tahoma 8.25'
        gsettings set org.gnome.desktop.interface document-font-name 'Tahoma 8.25'
        gsettings set org.gnome.desktop.interface monospace-font-name 'Lucida Console 9.75'
        gsettings set org.gnome.desktop.wm.preferences titlebar-font 'Trebuchet MS Bold 9.75'
        gsettings set org.gnome.desktop.interface font-hinting 'full'
        gsettings set org.gnome.desktop.interface font-antialiasing 'grayscale'
        ;;
    gtk)
        # preservar o tema do Shell (gnome-shell/) que vive na mesma pasta
        KEEP=""
        if [ -d "$HOME/.themes/WindowsXP-Luna/gnome-shell" ]; then
            KEEP="$(mktemp -d)"
            mv "$HOME/.themes/WindowsXP-Luna/gnome-shell" "$KEEP/"
        fi
        install_dir "$BUILD/gtk/WindowsXP-Luna" "$HOME/.themes/WindowsXP-Luna"
        if [ -n "$KEEP" ]; then
            mv "$KEEP/gnome-shell" "$HOME/.themes/WindowsXP-Luna/"
            rmdir "$KEEP"
        fi
        # O zorin-auto-theme repõe o tema Zorin ao nascer/pôr do sol: desligar
        gsettings set com.zorin.desktop.auto-theme enabled false 2>/dev/null || true
        gsettings set org.gnome.desktop.interface gtk-theme 'WindowsXP-Luna'
        gsettings set org.gnome.desktop.interface color-scheme 'default'
        gsettings set org.gnome.desktop.wm.preferences theme 'WindowsXP-Luna'
        # Ordem dos botões do XP (o ícone é desenhado pela extensão)
        gsettings set org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'
        # Como no XP, as janelas de diálogo são janelas normais que se podem
        # arrastar (o GNOME cola-as ao centro da janela-mãe); o valor original
        # fica na cópia de segurança do dconf (/org/gnome/mutter/)
        gsettings set org.gnome.mutter attach-modal-dialogs false
        # Barras de deslocamento sempre visíveis, como no XP
        gsettings set org.gnome.desktop.interface overlay-scrolling false
        # O libadwaita do Zorin só procura temas em /usr/share/themes: o tema GTK4
        # entra como folha de utilizador (carregada por todas as apps GTK4)
        mkdir -p "$HOME/.config/gtk-4.0"
        printf '/* Zorin XP — gerado pelo install.sh */\n@import url("file://%s/.themes/WindowsXP-Luna/gtk-4.0/gtk.css");\n' \
            "$HOME" > "$HOME/.config/gtk-4.0/gtk.css"
        record "$HOME/.config/gtk-4.0/gtk.css"
        ;;
    shell)
        # vai para dentro do mesmo tema (o user-theme procura ~/.themes/<nome>/gnome-shell)
        mkdir -p "$HOME/.themes/WindowsXP-Luna"
        install_dir "$BUILD/shell/WindowsXP-Luna/gnome-shell" "$HOME/.themes/WindowsXP-Luna/gnome-shell"
        record "$HOME/.themes/WindowsXP-Luna"
        # o User Themes só relê o CSS quando o nome muda: forçar a recarga
        gsettings set org.gnome.shell.extensions.user-theme name ''
        sleep 1
        gsettings set org.gnome.shell.extensions.user-theme name 'WindowsXP-Luna'
        # Layout "Windows" da Aparência do Zorin (menu + barra de tarefas, ao
        # estilo do Windows 7) com os ajustes do XP: barra de 30 px, botões de
        # 120 px com texto, "Ver ADT" visível, sem Atividades (tools/setup/zorin_layout.py)
        python3 "$HERE/tools/setup/zorin_layout.py"
        ;;
    extension)
        install_dir "$BUILD/extension/zorin-xp@zorin-xp.local" \
            "$HOME/.local/share/gnome-shell/extensions/zorin-xp@zorin-xp.local"
        # imagens que a extensão gera no tamanho exato (sombra e barras do menu)
        record "$HOME/.cache/zorin-xp"
        # Definições da zorin-taskbar como folha de propriedades do XP: o Shell
        # do Zorin não aceita uma cópia da extensão na pasta pessoal, por isso
        # só as definições vêm de uma cópia (prefs.js original renomeado para
        # prefs-zorin.js, sem alterações, e o nosso por cima), para onde a
        # extensão Zorin XP aponta o processo das definições. Voltar a instalar
        # depois de uma atualização do Zorin copia a versão nova.
        ZT_SYS=/usr/share/gnome-shell/extensions/zorin-taskbar@zorinos.com
        # (o caminho tem de conter /gnome-shell/extensions/<UUID>: é assim que o
        # GNOME descobre a extensão nas traduções e no lookupByURL; fica fora da
        # pasta de extensões que o Shell lê)
        ZT_PREFS="$HOME/.local/share/zorin-xp/gnome-shell/extensions/zorin-taskbar@zorinos.com"
        ZT_OLD="$HOME/.local/share/gnome-shell/extensions/zorin-taskbar@zorinos.com"
        if [ -f "$ZT_OLD/.zorin-xp" ]; then
            rm -rf "$ZT_OLD"   # cópias de versões anteriores deste instalador
        fi
        rm -rf "$HOME/.local/share/zorin-xp/zorin-taskbar-prefs" \
            "$HOME/.local/share/zorin-xp/zorin-taskbar@zorinos.com"   # versões anteriores
        if [ -f "$ZT_SYS/prefs.js" ]; then
            rm -rf "$ZT_PREFS"
            mkdir -p "$(dirname "$ZT_PREFS")"
            cp -a "$ZT_SYS" "$ZT_PREFS"
            mv "$ZT_PREFS/prefs.js" "$ZT_PREFS/prefs-zorin.js"
            cp "$HERE/src/zorin-taskbar-xp/prefs.js" "$ZT_PREFS/prefs.js"
            # traduções: as do sistema e, para português, a nossa em pt-PT (a
            # Zorin só traz pt_BR incompleta). Com uma pasta locale/ na cópia,
            # o GNOME procura as traduções só aí.
            for mo in /usr/share/locale/*/LC_MESSAGES/zorin-taskbar.mo; do
                [ -f "$mo" ] || continue
                lang=$(basename "$(dirname "$(dirname "$mo")")")
                mkdir -p "$ZT_PREFS/locale/$lang/LC_MESSAGES"
                cp "$mo" "$ZT_PREFS/locale/$lang/LC_MESSAGES/"
            done
            for lang in pt pt_PT; do
                mkdir -p "$ZT_PREFS/locale/$lang/LC_MESSAGES"
                python3 "$HERE/tools/setup/pomo.py" "$HERE/src/zorin-taskbar-xp/pt.po" \
                    "$ZT_PREFS/locale/$lang/LC_MESSAGES/zorin-taskbar.mo"
            done
            record "$ZT_PREFS"
        fi
        # Ecrã de carregamento do XP desde o primeiro instante da sessão (o
        # arranque X11 do GDM lê o ~/.xprofile); fecha-se quando a extensão
        # mostra o dela. Bloco marcado, retirado pelo restore.sh.
        install -m 755 "$HERE/src/session-splash/zorin-xp-splash" "$HOME/.local/bin/zorin-xp-splash"
        record "$HOME/.local/bin/zorin-xp-splash"
        if ! grep -qF '# >>> zorin-xp' "$HOME/.xprofile" 2>/dev/null; then
            if [ ! -e "$HOME/.xprofile" ]; then
                touch "$HOME/.xprofile"
                record "$HOME/.xprofile"
            fi
            cat >> "$HOME/.xprofile" <<'XPROFILE'
# >>> zorin-xp: ecrã de carregamento do XP enquanto a sessão arranca
if [ -x "$HOME/.local/bin/zorin-xp-splash" ]; then ("$HOME/.local/bin/zorin-xp-splash" >/dev/null 2>&1 &); fi
# <<< zorin-xp
XPROFILE
        fi
        # Aparência do Zorin como folha de propriedades do XP: um comando
        # zorin-appearance na pasta pessoal (antes de /usr/bin no PATH) que
        # corre a aplicação da Zorin e só reorganiza a janela; o atalho do menu
        # de aplicações aponta para ele pelo caminho completo
        mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
        install -m 755 "$HERE/src/zorin-appearance-xp/zorin-appearance" "$HOME/.local/bin/zorin-appearance"
        record "$HOME/.local/bin/zorin-appearance"
        if [ -f /usr/share/applications/zorin-appearance.desktop ]; then
            sed "s|^Exec=.*|Exec=$HOME/.local/bin/zorin-appearance|" \
                /usr/share/applications/zorin-appearance.desktop \
                > "$HOME/.local/share/applications/zorin-appearance.desktop"
            record "$HOME/.local/share/applications/zorin-appearance.desktop"
        fi
        python3 - <<'PY'
import ast, subprocess
key = ("org.gnome.shell", "enabled-extensions")
cur = ast.literal_eval(subprocess.check_output(["gsettings", "get", *key], text=True).strip().replace("@as ", ""))
if "zorin-xp@zorin-xp.local" not in cur:
    cur.append("zorin-xp@zorin-xp.local")
subprocess.check_call(["gsettings", "set", *key, str(cur)])
PY
        ;;
    logon)
        # Ecrã bloqueado = ecrã de boas-vindas do XP (a mesma extensão, na sessão)
        install_dir "$BUILD/logon/zorin-xp-logon@zorin-xp.local" \
            "$HOME/.local/share/gnome-shell/extensions/zorin-xp-logon@zorin-xp.local"
        python3 - <<'PY'
import ast, subprocess
key = ("org.gnome.shell", "enabled-extensions")
cur = ast.literal_eval(subprocess.check_output(["gsettings", "get", *key], text=True).strip().replace("@as ", ""))
if "zorin-xp-logon@zorin-xp.local" not in cur:
    cur.append("zorin-xp-logon@zorin-xp.local")
subprocess.check_call(["gsettings", "set", *key, str(cur)])
PY
        # Ecrã de início de sessão: corre como o utilizador gdm, por isso
        # vai para a pasta dele (/var/lib/gdm3) com sudo; o restore.sh desfaz
        echo "Ecrã de início de sessão (precisa da palavra-passe de administrador):"
        if sudo "$HERE/system/logon.sh" install "$BUILD/logon" "$HOME/.local/share/icons/WindowsXP-Cursors"; then
            touch "$STATE_DIR/logon-installed"
        else
            echo "  ecrã de início de sessão não instalado" >&2
        fi
        ;;
    boot)
        # Ecrã de arranque do XP (Plymouth): pasta nova em
        # /usr/share/plymouth/themes + initramfs, com sudo; o restore.sh desfaz
        echo "Ecrã de arranque (precisa da palavra-passe de administrador):"
        if sudo "$HERE/system/bootscreen.sh" install "$BUILD/boot"; then
            touch "$STATE_DIR/boot-installed"
        else
            echo "  ecrã de arranque não instalado" >&2
        fi
        ;;
    icons)
        install_dir "$BUILD/icons/WindowsXP" "$HOME/.local/share/icons/WindowsXP"
        gtk-update-icon-cache -q "$HOME/.local/share/icons/WindowsXP" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface icon-theme 'WindowsXP'
        # tipos do Office que o sistema não conhece (.accdb, .one, .msg, .pst):
        # para terem o ícone e o nome que tinham no XP
        install_file "$HERE/src/mime/zorin-xp-office.xml" "$HOME/.local/share/mime/packages/zorin-xp-office.xml"
        update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
        ;;
    folders)
        # pastas pessoais com os nomes do XP (os nomes antigos ficam como
        # atalhos escondidos: nada se quebra; tools/setup/xpfolders.py undo repõe)
        python3 "$HERE/tools/setup/xpfolders.py" apply
        # "O meu computador" e "Reciclagem" no Ficheiros e no ambiente de
        # trabalho: cópias das traduções do sistema com os nomes do XP e a
        # biblioteca que faz só esses programas usá-las
        rm -rf "$STATE_DIR/locale"
        python3 "$HERE/tools/setup/molocale.py" "$STATE_DIR/locale" >/dev/null
        record "$STATE_DIR/locale"
        if command -v cc >/dev/null; then
            mkdir -p "$STATE_DIR/gettext"
            cc -O2 -shared -fPIC -o "$STATE_DIR/gettext/zorin-xp-gettext.so" \
                "$HERE/src/gettext-shim/zorin-xp-gettext.c" -ldl
            record "$STATE_DIR/gettext"
            PRE="/usr/bin/env LD_PRELOAD=$STATE_DIR/gettext/zorin-xp-gettext.so ZXP_LOCALEDIR=$STATE_DIR/locale ZXP_GETTEXT_DOMAINS=nautilus"
            mkdir -p "$HOME/.local/share/dbus-1/services"
            for svc in org.gnome.Nautilus org.freedesktop.FileManager1; do
                printf '[D-BUS Service]\nName=%s\nExec=%s /usr/bin/nautilus --gapplication-service\n' \
                    "$svc" "$PRE" > "$HOME/.local/share/dbus-1/services/$svc.service"
                record "$HOME/.local/share/dbus-1/services/$svc.service"
            done
            # (o barramento só vigia pastas que já existiam quando arrancou)
            gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
                --method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1 || true
            mkdir -p "$HOME/.local/bin"
            printf '#!/bin/sh\n# Zorin XP: o Ficheiros com os nomes do XP (install.sh, componente folders)\nexec %s /usr/bin/nautilus "$@"\n' \
                "$PRE" > "$HOME/.local/bin/nautilus"
            chmod +x "$HOME/.local/bin/nautilus"
            record "$HOME/.local/bin/nautilus"
        else
            echo "  (sem compilador de C: o Ficheiros fica com 'Pasta pessoal' e 'Lixo')" >&2
        fi
        # legendas dos ícones do ambiente de trabalho como no XP (bloco marcado)
        GTK3CSS="$HOME/.config/gtk-3.0/gtk.css"
        mkdir -p "$(dirname "$GTK3CSS")"
        [ -f "$GTK3CSS" ] && sed -i '/^\/\* >>> zorin-xp: ícones do ambiente de trabalho/,/^\/\* <<< zorin-xp \*\//d' "$GTK3CSS"
        cat "$HERE/src/desktop/gtk3-desktop-labels.css" >> "$GTK3CSS"
        # grelha do XP: cópia do programa dos ícones com células mais pequenas
        # (a extensão usa-a enquanto corresponder à do Zorin: desktopNames.js)
        # (e o resto do ambiente de trabalho do XP: src/desktop/zxpDesktop.js)
        if python3 "$HERE/tools/setup/dingcopy.py" "$STATE_DIR/ding"; then
            record "$STATE_DIR/ding"
        fi
        # ícones do Ficheiros com 48 px (como os do ambiente de trabalho)
        gsettings set org.gnome.nautilus.icon-view default-zoom-level 'small'
        # o Ficheiros e o ambiente de trabalho voltam a abrir com os nomes novos
        nautilus -q 2>/dev/null || true
        pkill -f "(zorin-desktop-icons@zorinos.com|zorin-xp/ding)/app/ding.js" 2>/dev/null || true
        ;;
    explorer)
        # o Ficheiros como o Explorador do XP: a extensão do nautilus-python
        # (barras, painel de tarefas, vistas, menus, som ao mudar de pasta) e,
        # como no XP, sem miniaturas de PDF nos ícones (vão para os Detalhes)
        install_file "$HERE/src/nautilus-xp/zorin_xp_explorer.py" \
            "$HOME/.local/share/nautilus-python/extensions/zorin_xp_explorer.py"
        record "$HOME/.local/share/nautilus-python/extensions/__pycache__"
        python3 "$HERE/tools/setup/explorerprefs.py" apply
        nautilus -q 2>/dev/null || true
        ;;
    zen)
        # Zen Browser com o aspeto do Internet Explorer 6 (CSS: userChrome.css
        # do perfil; botões do IE na barra; preferências em tools/setup/zenprefs.py)
        P=$(zen_profile || true)
        if [ -z "$P" ]; then
            echo "  (Zen Browser não encontrado: ignorado)"
        elif pgrep -f "^/app/zen/zen" >/dev/null; then
            echo "  O Zen está aberto: feche-o e volte a correr ./install.sh zen" >&2
        else
            install_dir "$BUILD/zen/fonts" "$HOME/.local/share/fonts/zorin-xp-ie"
            fc-cache -f "$HOME/.local/share/fonts/zorin-xp-ie" >/dev/null 2>&1 || true
            install_dir "$BUILD/zen/zorin-xp-ie" "$P/chrome/zorin-xp-ie"
            # o clique do IE ao abrir uma página; as barras Favoritos e Histórico;
            # Localizar; a pasta do "Guardar como" lembrada por sítio; o aviso
            # de novo separador; o pino da barra dos separadores; o título do IE;
            # as barras de deslocamento do XP
            for x in sounds favorites history find lastdir tabflash sidebarpin title scrollbars; do
                install_file "$BUILD/zen/zorin-xp-ie-$x@zorin-xp.local.xpi" \
                    "$P/extensions/zorin-xp-ie-$x@zorin-xp.local.xpi"
            done
            # a janela (userChrome.css) e o que vai dentro das páginas (userContent.css)
            for x in "userChrome.css ie.css" "userContent.css content.css"; do
                read -r file css <<< "$x"
                UC="$P/chrome/$file"
                [ -f "$UC" ] || { : > "$UC"; record "$UC"; }
                sed -i '/^\/\* >>> zorin-xp: Internet Explorer/,/^\/\* <<< zorin-xp \*\//d' "$UC"
                # (os @import têm de vir antes de tudo o resto)
                { printf '/* >>> zorin-xp: Internet Explorer (install.sh) */\n@import url("zorin-xp-ie/%s");\n/* <<< zorin-xp */\n' "$css"; cat "$UC"; } > "$UC.zxp" && mv "$UC.zxp" "$UC"
            done
            python3 "$HERE/tools/setup/zenprefs.py" apply "$P"
            # "ZXP Tahoma" (a Tahoma sem suavização) nas regras de letras dos browsers
            install_file "$HERE/src/fontconfig/zorin-xp-browser-fonts" "$HOME/.local/bin/zorin-xp-browser-fonts"
            "$HOME/.local/bin/zorin-xp-browser-fonts" >/dev/null
        fi
        ;;
    filechooser)
        # janela "Abrir"/"Guardar como" do XP como portal de ficheiros (em vez
        # da do GNOME, que fica de reserva se esta falhar)
        FC="$STATE_DIR/filechooser"
        install_dir "$BUILD/filechooser/zorin-xp-filechooser" "$FC"
        mkdir -p "$HOME/.local/share/dbus-1/services"
        printf '[D-BUS Service]\nName=org.freedesktop.impl.portal.desktop.zorinxp\nExec=%s/zorin-xp-filechooser\n' \
            "$FC" > "$HOME/.local/share/dbus-1/services/org.freedesktop.impl.portal.desktop.zorinxp.service"
        record "$HOME/.local/share/dbus-1/services/org.freedesktop.impl.portal.desktop.zorinxp.service"
        gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
            --method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1 || true
        # o xdg-desktop-portal só lê portais de uma pasta: a do sistema (ligações)
        # mais o nosso, indicada ao serviço por XDG_DESKTOP_PORTAL_DIR
        PD="$STATE_DIR/portals"
        rm -rf "$PD"; mkdir -p "$PD"
        for f in /usr/share/xdg-desktop-portal/portals/*.portal; do ln -s "$f" "$PD/"; done
        printf '[portal]\nDBusName=org.freedesktop.impl.portal.desktop.zorinxp\nInterfaces=org.freedesktop.impl.portal.FileChooser;\nUseIn=gnome;zorin\n' \
            > "$PD/zorinxp.portal"
        record "$PD"
        DROP="$HOME/.config/systemd/user/xdg-desktop-portal.service.d"
        mkdir -p "$DROP"
        printf '[Service]\nEnvironment=XDG_DESKTOP_PORTAL_DIR=%s\n' "$PD" > "$DROP/zorin-xp.conf"
        record "$DROP/zorin-xp.conf"
        # preferências: as do sistema, com a janela de ficheiros entregue ao XP
        # (com XDG_DESKTOP_PORTAL_DIR, o serviço lê o portals.conf dessa pasta)
        SYS=$(ls /usr/share/xdg-desktop-portal/*portals.conf 2>/dev/null | head -1)
        { if [ -n "$SYS" ]; then grep -v 'impl.portal.FileChooser' "$SYS"; else printf '[preferred]\ndefault=gnome;gtk;\n'; fi
          echo 'org.freedesktop.impl.portal.FileChooser=zorinxp;'; } > "$PD/portals.conf"
        # aplicações GTK normais: também pedem a janela ao portal (após novo login)
        mkdir -p "$HOME/.config/environment.d"
        printf 'GTK_USE_PORTAL=1\nGDK_DEBUG=portals\n' > "$HOME/.config/environment.d/60-zorin-xp-filechooser.conf"
        record "$HOME/.config/environment.d/60-zorin-xp-filechooser.conf"
        systemctl --user daemon-reload
        systemctl --user restart xdg-desktop-portal.service 2>/dev/null || true
        ;;
    *)
        echo "Componente '$c' desconhecido" >&2
        ;;
    esac
    echo "  ✓ instalado: $c"
done

echo
echo "Feito. Para reverter tudo: $UNINSTALL/rescue/restore.sh"
echo "(funciona mesmo sem esta pasta; também está em $HERE/rescue/restore.sh)"
