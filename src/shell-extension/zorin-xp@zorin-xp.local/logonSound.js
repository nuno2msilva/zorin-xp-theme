/*
 * XP's logon sound, when the desktop appears:
 *   - first logon after turning the computer on: "Iniciar o Windows"
 *     (Windows XP Startup.wav, the theme's desktop-login event);
 *   - later logons: "Início de sessão do Windows" (Windows XP Logon
 *     Sound.wav, the service-login event).
 * Only when the Shell starts: unlocking the screen enables the extensions
 * again and must not play; restarting the Shell (Alt+F2 r) in the same
 * session must not either.
 */
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const BOOT_ID = '/proc/sys/kernel/random/boot_id';

function readText(path) {
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        return ok ? new TextDecoder().decode(bytes).trim() : '';
    } catch (e) {
        return '';
    }
}

function writeText(path, text) {
    try {
        GLib.mkdir_with_parents(GLib.path_get_dirname(path), 0o755);
        GLib.file_set_contents(path, text);
    } catch (e) {
        logError(e, 'Zorin XP: som de início de sessão');
    }
}

const MARKER = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'zorin-xp-logon-sound']);
const SESSION = GLib.getenv('XDG_SESSION_ID') || 'sessão';

// is the Shell starting for the first time in this session? (not when
// restarting the Shell with Alt+F2 r, nor when unlocking the screen)
export function isSessionStart() {
    return Main.layoutManager._startingUp && readText(MARKER) !== SESSION;
}

export function playLogonSound() {
    if (!isSessionStart())
        return;
    writeText(MARKER, SESSION);

    // first logon since the computer started?
    const lastBoot = GLib.build_filenamev([GLib.get_user_data_dir(), 'zorin-xp', 'last-boot']);
    const boot = readText(BOOT_ID);
    const firstSinceBoot = readText(lastBoot) !== boot;
    writeText(lastBoot, boot);

    const id = Main.layoutManager.connect('startup-complete', () => {
        Main.layoutManager.disconnect(id);
        global.display.get_sound_player().play_from_theme(
            firstSinceBoot ? 'desktop-login' : 'service-login',
            firstSinceBoot ? 'Iniciar o Windows' : 'Início de sessão do Windows',
            null);
    });
}
