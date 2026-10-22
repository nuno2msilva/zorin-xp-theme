/*
 * Definições da zorin-taskbar como folha de propriedades do XP.
 *
 * O GNOME Shell do Zorin não aceita uma cópia na pasta pessoal de uma
 * extensão da sessão ("not loading … as part of session mode"). Por isso o
 * Shell continua a correr a zorin-taskbar do sistema e só as definições vêm
 * da cópia em ~/.local/share/zorin-xp/gnome-shell/extensions/<UUID> (prefs.js original
 * renomeado + o nosso, ver src/zorin-taskbar-xp/prefs.js): o processo das
 * definições pergunta ao Shell, por D-Bus, onde está a extensão.
 */
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const UUID = 'zorin-taskbar@zorinos.com';
// (o caminho tem de conter /gnome-shell/extensions/<UUID>: é assim que o
// GNOME encontra a extensão nas traduções e no lookupByURL)
const PREFS_DIR = `${GLib.get_user_data_dir()}/zorin-xp/gnome-shell/extensions/${UUID}`;

export class PrefsRedirect {
    constructor() {
        const svc = Main.shellDBusService?._extensionsService;
        if (!svc || !GLib.file_test(`${PREFS_DIR}/prefs.js`, GLib.FileTest.EXISTS))
            return;
        this._svc = svc;
        const orig = Object.getPrototypeOf(svc).GetExtensionInfo;
        svc.GetExtensionInfo = function (uuid) {
            const info = orig.call(this, uuid);
            if (uuid === UUID && info.path)
                info.path = new GLib.Variant('s', PREFS_DIR);
            return info;
        };
    }

    destroy() {
        if (this._svc)
            delete this._svc.GetExtensionInfo;
        this._svc = null;
    }
}
