/*
 * Som de início de sessão do XP, quando o ambiente de trabalho aparece:
 *   - primeiro início de sessão depois de ligar o computador: "Iniciar o
 *     Windows" (Windows XP Startup.wav, evento desktop-login do tema);
 *   - inícios de sessão seguintes: "Início de sessão do Windows" (Windows XP
 *     Logon Sound.wav, evento service-login).
 * Só no arranque do Shell: desbloquear o ecrã volta a ativar as extensões e
 * não deve tocar; reiniciar o Shell (Alt+F2 r) na mesma sessão também não.
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

// o Shell está a arrancar pela primeira vez nesta sessão? (não ao reiniciar
// o Shell com Alt+F2 r, nem ao desbloquear o ecrã)
export function isSessionStart() {
    return Main.layoutManager._startingUp && readText(MARKER) !== SESSION;
}

export function playLogonSound() {
    if (!isSessionStart())
        return;
    writeText(MARKER, SESSION);

    // primeiro início de sessão desde que o computador arrancou?
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
