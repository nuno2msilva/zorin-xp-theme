#!/bin/bash
# Test Zen: no window (headless), its own profile, Marionette on port 2829
T="$HOME/.var/app/app.zen_browser.zen/zxp-test-profile"
# (window icons in another folder: the normal one is the user's Zen's)
exec flatpak run ${ZXP_FT:+--env=FREETYPE_PROPERTIES=$ZXP_FT} --env=ZXP_FAVICON_DIR="$HOME/.var/app/app.zen_browser.zen/cache/zorin-xp-favicons-test" app.zen_browser.zen --headless --marionette -remote-allow-system-access --no-remote --profile "$T" "$@"
