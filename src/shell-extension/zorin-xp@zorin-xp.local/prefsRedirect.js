/*
 * zorin-taskbar settings as an XP property sheet.
 *
 * Zorin's GNOME Shell does not accept a home-folder copy of a session
 * extension ("not loading … as part of session mode"). So the Shell keeps
 * running the system's zorin-taskbar and only the settings come from the
 * copy in ~/.local/share/zorin-xp/gnome-shell/extensions/<UUID> (original
 * prefs.js renamed + ours, see src/zorin-taskbar-xp/prefs.js): the settings
 * process asks the Shell, over D-Bus, where the extension is.
 */
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const UUID = 'zorin-taskbar@zorinos.com';
// (the path must contain /gnome-shell/extensions/<UUID>: that is how
// GNOME finds the extension for translations and lookupByURL)

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
