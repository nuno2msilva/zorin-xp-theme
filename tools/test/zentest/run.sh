#!/bin/bash
# Zen de teste: sem janela (headless), perfil próprio, Marionette na porta 2829
T="$HOME/.var/app/app.zen_browser.zen/zxp-test-profile"
# (os ícones das janelas noutra pasta: a normal é a do Zen do utilizador)
exec flatpak run ${ZXP_FT:+--env=FREETYPE_PROPERTIES=$ZXP_FT} --env=ZXP_FAVICON_DIR="$HOME/.var/app/app.zen_browser.zen/cache/zorin-xp-favicons-test" app.zen_browser.zen --headless --marionette -remote-allow-system-access --no-remote --profile "$T" "$@"
