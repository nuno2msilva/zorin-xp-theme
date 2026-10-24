/*
 * The XP file dialog also in the applications that make GTK 3's chooser
 * themselves (VS Code, other Electron apps): install.sh filechooser builds a
 * GTK 3 module for that (src/filechooser/zorin-xp-filechooser-module.c),
 * which GTK only loads if GTK3_MODULES names it when the application starts.
 * The Shell starts the applications of the menu, the taskbar and the
 * overview with its own environment, fixed when the session started: here
 * the module goes into it, so they all get it — also in a session that
 * started before the module was installed (after the Shell restarts).
 */
import GLib from 'gi://GLib';

const MODULE = GLib.build_filenamev([GLib.get_user_data_dir(), 'zorin-xp', 'filechooser',
    'libzorin-xp-filechooser-module.so']);

export class FileDialogModule {
    constructor() {
        this._old = GLib.getenv('GTK3_MODULES');
        const mods = (this._old ?? '').split(':').filter(m => m);
        this._set = GLib.file_test(MODULE, GLib.FileTest.EXISTS) && !mods.includes(MODULE);
        if (this._set)
            GLib.setenv('GTK3_MODULES', [MODULE, ...mods].join(':'), true);
    }

    destroy() {
        if (!this._set)
            return;
        if (this._old === null)
            GLib.unsetenv('GTK3_MODULES');
        else
            GLib.setenv('GTK3_MODULES', this._old, true);
        this._set = false;
    }
}
