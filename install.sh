#!/usr/bin/env bash
# Zorin XP — installer.
# Usage: ./install.sh [components...]
# Builds the theme from assets/ (the XP resources, already extracted: to
# extract them again from a copy of Windows, tools/extract.py) and installs it.
# Components: sounds cursors fonts gtk shell extension icons folders explorer filechooser zen logon boot
#   (default: all; logon (login screen) and boot (boot screen, Plymouth)
#   ask for the administrator password)
# Everything is copied (into the home folder and, with sudo, into system
# folders): nothing depends on this folder afterwards. What is installed is
# recorded in ~/.local/share/zorin-xp/installed-files.txt; rescue/restore.sh
# (also copied to ~/.local/share/zorin-xp/uninstall) removes it and restores
# the original settings.
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

# Original snapshot before the first change
if [ ! -e "$STATE_DIR/backup/original" ]; then
    "$HERE/rescue/backup.sh"
fi

# Standalone uninstaller: restore.sh and the helpers it calls, in the same
# relative folders, so the theme can be reverted even after this folder is
# deleted (nothing that is installed depends on it)
UNINSTALL="$STATE_DIR/uninstall"
rm -rf "$UNINSTALL"
for f in rescue/restore.sh src/fontconfig/zorin-xp-browser-fonts \
         tools/setup/explorerprefs.py tools/setup/zenprefs.py tools/setup/xpfolders.py \
         system/logon.sh system/bootscreen.sh; do
    install -D -m "$(stat -c %a "$HERE/$f")" "$HERE/$f" "$UNINSTALL/$f"
done

record() {  # records an installed path (once)
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

zen_profile() {  # folder of Zen's default profile (Flatpak), or nothing
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
        # (the click when changing folders in Files: Shell extension, navigationSound.js)
        gsettings set org.gnome.desktop.sound theme-name 'WindowsXP'
        gsettings set org.gnome.desktop.sound event-sounds true
        ;;
    cursors)
        install_dir "$BUILD/cursors/WindowsXP" "$HOME/.local/share/icons/WindowsXP-Cursors"
        # Xcursor (the cursors of X11 applications) only looks in ~/.icons
        # and /usr/share/icons: without this link applications did not find the
        # theme and fell back to the default cursors (black, none of XP's)
        if [ ! -e "$HOME/.icons/WindowsXP-Cursors" ] || [ -L "$HOME/.icons/WindowsXP-Cursors" ]; then
            mkdir -p "$HOME/.icons"
            ln -sfn "$HOME/.local/share/icons/WindowsXP-Cursors" "$HOME/.icons/WindowsXP-Cursors"
            record "$HOME/.icons/WindowsXP-Cursors"
        fi
        gsettings set org.gnome.desktop.interface cursor-theme 'WindowsXP-Cursors'
        gsettings set org.gnome.desktop.interface cursor-size 32
        # applications that do not read gsettings (plain X11, Qt, Java, Wine): the
        # Xcursor "default" theme and the XCURSOR_* variables (active after a new login)
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
        # Flatpak: applications only see the themes in the home folder with permission
        # (only if the user has no global overrides yet — those are not touched)
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
        # TrueType interpreter v35 (horizontal hinting, like XP's GDI); active after a new login
        mkdir -p "$HOME/.config/environment.d"
        echo 'FREETYPE_PROPERTIES="truetype:interpreter-version=35"' \
            > "$HOME/.config/environment.d/60-zorin-xp-freetype.conf"
        record "$HOME/.config/environment.d/60-zorin-xp-freetype.conf"
        # ...but browser engines (Electron/Chromium, Firefox) place letters at
        # fractional pixels and with v35 the spacing becomes irregular: those
        # applications keep the normal interpreter (run the command again
        # after installing new applications)
        # (the XP fonts as they come, for the applications with a browser engine:
        # outside the font folders, only their own configuration reads them)
        install_dir "$BUILD/fonts/browser" "$HOME/.local/share/zorin-xp/browser-fonts"
        install_file "$HERE/src/fontconfig/zorin-xp-browser-fonts" "$HOME/.local/bin/zorin-xp-browser-fonts"
        "$HOME/.local/bin/zorin-xp-browser-fonts"
        fc-cache -f "$HOME/.local/share/fonts" >/dev/null
        # Whole px sizes as in XP at 96 dpi: 8 pt = 11 px, 10 pt = 13 px
        gsettings set org.gnome.desktop.interface font-name 'Tahoma 8.25'
        gsettings set org.gnome.desktop.interface document-font-name 'Tahoma 8.25'
        gsettings set org.gnome.desktop.interface monospace-font-name 'Lucida Console 9.75'
        gsettings set org.gnome.desktop.wm.preferences titlebar-font 'Trebuchet MS Bold 9.75'
        gsettings set org.gnome.desktop.interface font-hinting 'full'
        gsettings set org.gnome.desktop.interface font-antialiasing 'grayscale'
        ;;
    gtk)
        # keep the Shell theme (gnome-shell/) that lives in the same folder
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
        # zorin-auto-theme puts the Zorin theme back at sunrise/sunset: turn it off
        gsettings set com.zorin.desktop.auto-theme enabled false 2>/dev/null || true
        gsettings set org.gnome.desktop.interface gtk-theme 'WindowsXP-Luna'
        gsettings set org.gnome.desktop.interface color-scheme 'default'
        gsettings set org.gnome.desktop.wm.preferences theme 'WindowsXP-Luna'
        # XP button order (the icon is drawn by the extension)
        gsettings set org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'
        # As in XP, dialogs are normal windows that can be dragged (GNOME
        # attaches them to the centre of the parent window); the original value
        # stays in the dconf backup (/org/gnome/mutter/)
        gsettings set org.gnome.mutter attach-modal-dialogs false
        # Scrollbars always visible, as in XP
        gsettings set org.gnome.desktop.interface overlay-scrolling false
        # Zorin's libadwaita only looks for themes in /usr/share/themes: the GTK4
        # theme comes in as a user stylesheet (loaded by every GTK4 app)
        mkdir -p "$HOME/.config/gtk-4.0"
        printf '/* Zorin XP — gerado pelo install.sh */\n@import url("file://%s/.themes/WindowsXP-Luna/gtk-4.0/gtk.css");\n' \
            "$HOME" > "$HOME/.config/gtk-4.0/gtk.css"
        record "$HOME/.config/gtk-4.0/gtk.css"
        ;;
    shell)
        # goes inside the same theme (user-theme looks in ~/.themes/<name>/gnome-shell)
        mkdir -p "$HOME/.themes/WindowsXP-Luna"
        install_dir "$BUILD/shell/WindowsXP-Luna/gnome-shell" "$HOME/.themes/WindowsXP-Luna/gnome-shell"
        record "$HOME/.themes/WindowsXP-Luna"
        # User Themes only rereads the CSS when the name changes: force a reload
        gsettings set org.gnome.shell.extensions.user-theme name ''
        sleep 1
        gsettings set org.gnome.shell.extensions.user-theme name 'WindowsXP-Luna'
        # "Windows" layout of Zorin Appearance (menu + taskbar, Windows 7
        # style) with the XP adjustments: 30 px bar, 120 px buttons with text,
        # "Show Desktop" visible, no Activities (tools/setup/zorin_layout.py)
        python3 "$HERE/tools/setup/zorin_layout.py"
        ;;
    extension)
        install_dir "$BUILD/extension/zorin-xp@zorin-xp.local" \
            "$HOME/.local/share/gnome-shell/extensions/zorin-xp@zorin-xp.local"
        # images the extension generates at the exact size (menu shadow and bars)
        record "$HOME/.cache/zorin-xp"
        # zorin-taskbar settings as an XP property sheet: Zorin's Shell does
        # not accept a copy of the extension in the home folder, so only the
        # settings come from a copy (original prefs.js renamed to
        # prefs-zorin.js, unchanged, with ours on top), to which the Zorin XP
        # extension points the settings process. Installing again after a
        # Zorin update copies the new version.
        ZT_SYS=/usr/share/gnome-shell/extensions/zorin-taskbar@zorinos.com
        # (the path must contain /gnome-shell/extensions/<UUID>: that is how
        # GNOME finds the extension for translations and lookupByURL; it stays
        # outside the extensions folder the Shell reads)
        ZT_PREFS="$HOME/.local/share/zorin-xp/gnome-shell/extensions/zorin-taskbar@zorinos.com"
        ZT_OLD="$HOME/.local/share/gnome-shell/extensions/zorin-taskbar@zorinos.com"
        if [ -f "$ZT_OLD/.zorin-xp" ]; then
            rm -rf "$ZT_OLD"   # copies from earlier versions of this installer
        fi
        rm -rf "$HOME/.local/share/zorin-xp/zorin-taskbar-prefs" \
            "$HOME/.local/share/zorin-xp/zorin-taskbar@zorinos.com"   # earlier versions
        if [ -f "$ZT_SYS/prefs.js" ]; then
            rm -rf "$ZT_PREFS"
            mkdir -p "$(dirname "$ZT_PREFS")"
            cp -a "$ZT_SYS" "$ZT_PREFS"
            mv "$ZT_PREFS/prefs.js" "$ZT_PREFS/prefs-zorin.js"
            cp "$HERE/src/zorin-taskbar-xp/prefs.js" "$ZT_PREFS/prefs.js"
            # translations: the system's and, for Portuguese, ours in pt-PT
            # (Zorin only ships an incomplete pt_BR). With a locale/ folder in
            # the copy, GNOME looks for translations only there.
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
        # XP loading screen from the very first moment of the session (GDM's
        # X11 startup reads ~/.xprofile); it closes when the extension shows
        # its own. Marked block, removed by restore.sh.
        install -m 755 "$HERE/src/session-splash/zorin-xp-splash" "$HOME/.local/bin/zorin-xp-splash"
        record "$HOME/.local/bin/zorin-xp-splash"
        if ! grep -qF '# >>> zorin-xp' "$HOME/.xprofile" 2>/dev/null; then
            if [ ! -e "$HOME/.xprofile" ]; then
                touch "$HOME/.xprofile"
                record "$HOME/.xprofile"
            fi
            cat >> "$HOME/.xprofile" <<'XPROFILE'
# >>> zorin-xp: XP loading screen while the session starts
if [ -x "$HOME/.local/bin/zorin-xp-splash" ]; then ("$HOME/.local/bin/zorin-xp-splash" >/dev/null 2>&1 &); fi
# <<< zorin-xp
XPROFILE
        fi
        # Zorin Appearance as an XP property sheet: a zorin-appearance command
        # in the home folder (before /usr/bin in PATH) that runs Zorin's
        # application and only rearranges the window; the application menu
        # shortcut points to it by its full path
        mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
        install -m 755 "$HERE/src/zorin-appearance-xp/zorin-appearance" "$HOME/.local/bin/zorin-appearance"
        record "$HOME/.local/bin/zorin-appearance"
        # (its "Windows" scheme applies the XP layout: the shell component's module)
        install_file "$HERE/tools/setup/zorin_layout.py" "$HOME/.local/share/zorin-xp/zorin_layout.py"
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
        # Lock screen = XP welcome screen (the same extension, in the session)
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
        # Login screen: it runs as the gdm user, so it goes into that user's
        # folder (/var/lib/gdm3) with sudo; restore.sh undoes it
        echo "Ecrã de início de sessão (precisa da palavra-passe de administrador):"
        if sudo "$HERE/system/logon.sh" install "$BUILD/logon" "$HOME/.local/share/icons/WindowsXP-Cursors"; then
            touch "$STATE_DIR/logon-installed"
        else
            echo "  ecrã de início de sessão não instalado" >&2
        fi
        ;;
    boot)
        # XP boot screen (Plymouth): new folder in
        # /usr/share/plymouth/themes + initramfs, with sudo; restore.sh undoes it
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
        # Office types the system does not know (.accdb, .one, .msg, .pst): so
        # they get the icon and the name they had in XP
        install_file "$HERE/src/mime/zorin-xp-office.xml" "$HOME/.local/share/mime/packages/zorin-xp-office.xml"
        update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
        ;;
    folders)
        # home folders with the XP names (the old names stay as hidden
        # shortcuts: nothing breaks; tools/setup/xpfolders.py undo restores them)
        python3 "$HERE/tools/setup/xpfolders.py" apply
        # "O meu computador" and "Reciclagem" in Files and on the desktop:
        # copies of the system translations with the XP names and the library
        # that makes only those programs use them
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
            # (the bus only watches folders that already existed when it started)
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
        # desktop icon labels as in XP (marked block)
        GTK3CSS="$HOME/.config/gtk-3.0/gtk.css"
        mkdir -p "$(dirname "$GTK3CSS")"
        [ -f "$GTK3CSS" ] && sed -i '/^\/\* >>> zorin-xp: ícones do ambiente de trabalho/,/^\/\* <<< zorin-xp \*\//d' "$GTK3CSS"
        cat "$HERE/src/desktop/gtk3-desktop-labels.css" >> "$GTK3CSS"
        # XP grid: copy of the icons program with smaller cells
        # (the extension uses it while it still matches Zorin's: desktopNames.js)
        # (and the rest of the XP desktop: src/desktop/zxpDesktop.js)
        if python3 "$HERE/tools/setup/dingcopy.py" "$STATE_DIR/ding"; then
            record "$STATE_DIR/ding"
        fi
        # Files icons at 48 px (like the desktop ones)
        gsettings set org.gnome.nautilus.icon-view default-zoom-level 'small'
        # Files and the desktop open again with the new names
        nautilus -q 2>/dev/null || true
        pkill -f "(zorin-desktop-icons@zorinos.com|zorin-xp/ding)/app/ding.js" 2>/dev/null || true
        ;;
    explorer)
        # Files as the XP Explorer: the nautilus-python extension (bars,
        # task pane, views, menus, sound when changing folders) and, as in
        # XP, no PDF thumbnails in the icons (they go to Details)
        install_file "$HERE/src/nautilus-xp/zorin_xp_explorer.py" \
            "$HOME/.local/share/nautilus-python/extensions/zorin_xp_explorer.py"
        record "$HOME/.local/share/nautilus-python/extensions/__pycache__"
        python3 "$HERE/tools/setup/explorerprefs.py" apply
        nautilus -q 2>/dev/null || true
        ;;
    zen)
        # Zen Browser with the look of Internet Explorer 6 (CSS: the profile's
        # userChrome.css; IE buttons on the toolbar; preferences in tools/setup/zenprefs.py)
        P=$(zen_profile || true)
        if [ -z "$P" ]; then
            echo "  (Zen Browser não encontrado: ignorado)"
        elif pgrep -f "^/app/zen/zen" >/dev/null; then
            echo "  O Zen está aberto: feche-o e volte a correr ./install.sh zen" >&2
        else
            install_dir "$BUILD/zen/fonts" "$HOME/.local/share/fonts/zorin-xp-ie"
            fc-cache -f "$HOME/.local/share/fonts/zorin-xp-ie" >/dev/null 2>&1 || true
            install_dir "$BUILD/zen/zorin-xp-ie" "$P/chrome/zorin-xp-ie"
            # one extension with the IE features (the click when a page opens,
            # the Favorites and History bars, Find, the "Save As" folder per
            # site, the new tab notice, the tab bar pin, the IE title, the XP
            # scrollbars), each turned on and off in its Preferences page
            install_file "$BUILD/zen/zorin-xp-ie@zorin-xp.local.xpi" "$P/extensions/zorin-xp-ie@zorin-xp.local.xpi"
            # (the nine extensions of earlier versions: Zen forgets them on its next start)
            for x in sounds favorites history find lastdir tabflash sidebarpin title scrollbars; do
                rm -f "$P/extensions/zorin-xp-ie-$x@zorin-xp.local.xpi"
            done
            # the window (userChrome.css) and what goes inside pages (userContent.css)
            for x in "userChrome.css ie.css" "userContent.css content.css"; do
                read -r file css <<< "$x"
                UC="$P/chrome/$file"
                [ -f "$UC" ] || { : > "$UC"; record "$UC"; }
                sed -i '/^\/\* >>> zorin-xp: Internet Explorer/,/^\/\* <<< zorin-xp \*\//d' "$UC"
                # (@import rules must come before everything else)
                { printf '/* >>> zorin-xp: Internet Explorer (install.sh) */\n@import url("zorin-xp-ie/%s");\n/* <<< zorin-xp */\n' "$css"; cat "$UC"; } > "$UC.zxp" && mv "$UC.zxp" "$UC"
            done
            python3 "$HERE/tools/setup/zenprefs.py" apply "$P"
            # "ZXP Tahoma" (Tahoma without smoothing) in the browsers' font rules
            install_file "$HERE/src/fontconfig/zorin-xp-browser-fonts" "$HOME/.local/bin/zorin-xp-browser-fonts"
            "$HOME/.local/bin/zorin-xp-browser-fonts" >/dev/null
        fi
        ;;
    filechooser)
        # XP "Open"/"Save As" dialog as the file chooser portal (instead of
        # GNOME's, which stays as a fallback if this one fails)
        FC="$STATE_DIR/filechooser"
        install_dir "$BUILD/filechooser/zorin-xp-filechooser" "$FC"
        mkdir -p "$HOME/.local/share/dbus-1/services"
        printf '[D-BUS Service]\nName=org.freedesktop.impl.portal.desktop.zorinxp\nExec=%s/zorin-xp-filechooser\n' \
            "$FC" > "$HOME/.local/share/dbus-1/services/org.freedesktop.impl.portal.desktop.zorinxp.service"
        record "$HOME/.local/share/dbus-1/services/org.freedesktop.impl.portal.desktop.zorinxp.service"
        gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
            --method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1 || true
        # xdg-desktop-portal only reads portals from one folder: the system's
        # (links) plus ours, given to the service by XDG_DESKTOP_PORTAL_DIR
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
        # preferences: the system's, with the file dialog handed to XP
        # (with XDG_DESKTOP_PORTAL_DIR, the service reads that folder's portals.conf)
        SYS=$(ls /usr/share/xdg-desktop-portal/*portals.conf 2>/dev/null | head -1)
        { if [ -n "$SYS" ]; then grep -v 'impl.portal.FileChooser' "$SYS"; else printf '[preferred]\ndefault=gnome;gtk;\n'; fi
          echo 'org.freedesktop.impl.portal.FileChooser=zorinxp;'; } > "$PD/portals.conf"
        # normal GTK applications: they also ask the portal for the dialog (after a new login)

        # applications that make GTK 3's dialog themselves (Electron ones such as
        # VS Code, ONLYOFFICE) never ask the portal: a GTK 3 module hands their
        # dialog to it too (src/filechooser/zorin-xp-filechooser-module.c; only
        # the C library's headers needed)
        MOD="$FC/libzorin-xp-filechooser-module.so"
        MODENV=""
        if cc -O2 -shared -fPIC -fvisibility=hidden -o "$MOD" "$HERE/src/filechooser/zorin-xp-filechooser-module.c" \
               -l:libgtk-3.so.0 -l:libgdk-3.so.0 -l:libgio-2.0.so.0 -l:libgobject-2.0.so.0 -l:libglib-2.0.so.0 2>/dev/null; then
            MODENV="GTK3_MODULES=$MOD\${GTK3_MODULES:+:\$GTK3_MODULES}\n"
            # Flatpaks do not get the session's environment: the ones that make GTK's
            # dialog themselves (and see the home folder), each with an override
            : > "$STATE_DIR/filechooser-flatpaks.txt"
            for app in org.onlyoffice.desktopeditors; do
                if flatpak info "$app" >/dev/null 2>&1; then
                    flatpak override --user --env=GTK3_MODULES="$MOD" "$app"
                    echo "$app" >> "$STATE_DIR/filechooser-flatpaks.txt"
                fi
            done
            record "$STATE_DIR/filechooser-flatpaks.txt"
        else
            echo "  (sem compilador C: as aplicações com o diálogo do GTK feito por elas ficam com ele)"
        fi
        mkdir -p "$HOME/.config/environment.d"
        printf "GTK_USE_PORTAL=1\nGDK_DEBUG=portals\n$MODENV" > "$HOME/.config/environment.d/60-zorin-xp-filechooser.conf"
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
