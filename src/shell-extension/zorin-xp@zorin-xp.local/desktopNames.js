/*
 * Desktop icons as in XP:
 *  - "O meu computador" and "Reciclagem" instead of "Pasta pessoal" and "Lixo";
 *  - XP's grid (smaller cells).
 *
 * The icons are drawn by a separate gjs process, which the
 * zorin-desktop-icons extension launches with a Gio.SubprocessLauncher. That
 * launcher gets the zorin-xp-gettext.so library (LD_PRELOAD), which makes the
 * process use the translations in ~/.local/share/zorin-xp/locale
 * (tools/setup/molocale.py), and the program is swapped for the copy with
 * XP's grid (tools/setup/dingcopy.py), if it still matches Zorin's files.
 * Then the process is relaunched (the Zorin extension launches it again by
 * itself). Nothing on the system is touched.
 */
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const UUID = 'zorin-desktop-icons@zorinos.com';
const DATA = GLib.build_filenamev([GLib.get_user_data_dir(), 'zorin-xp']);
const SHIM = GLib.build_filenamev([DATA, 'gettext', 'zorin-xp-gettext.so']);
const LOCALE = GLib.build_filenamev([DATA, 'locale']);
const DING = GLib.build_filenamev([DATA, 'ding']);
const DING_APP = GLib.build_filenamev([DING, 'app']);
const DOMAINS = 'zorin-desktop-icons:nautilus';
const RETRY_MS = 1000;

function namesReady() {
    return GLib.file_test(SHIM, GLib.FileTest.EXISTS) && GLib.file_test(LOCALE, GLib.FileTest.IS_DIR);
}

// The copy only counts if Zorin's files are the same as when it was made
function copyMatches(src) {
    try {
        const [, bytes] = GLib.file_get_contents(GLib.build_filenamev([DING, 'stamp.json']));
        const stamp = JSON.parse(new TextDecoder().decode(bytes));
        if (stamp.src !== src)
            return false;
        const iter = Gio.File.new_for_path(src).enumerate_children(
            'standard::name,standard::size,time::modified', Gio.FileQueryInfoFlags.NONE, null);
        let n = 0;
        for (let info; (info = iter.next_file(null));) {
            const want = stamp.files[info.get_name()];
            if (!want || want[0] !== info.get_size() ||
                want[1] !== info.get_attribute_uint64('time::modified'))
                return false;
            n++;
        }
        return n === Object.keys(stamp.files).length;
    } catch (e) {
        return false;
    }
}

function cmdline(pid) {
    try {
        const [, bytes] = GLib.file_get_contents(`/proc/${pid}/cmdline`);
        return new TextDecoder().decode(bytes).split('\0');
    } catch (e) {
        return [];
    }
}

function prepare(launch, argv) {
    launch._zxpPrepared = true;
    if (namesReady()) {
        launch._launcher.setenv('LD_PRELOAD', SHIM, true);
        launch._launcher.setenv('ZXP_LOCALEDIR', LOCALE, true);
        launch._launcher.setenv('ZXP_GETTEXT_DOMAINS', DOMAINS, true);
    }
    const src = GLib.path_get_dirname(argv[0]);
    if (copyMatches(src))
        argv = argv.map(a => a === src || a.startsWith(`${src}/`) ? DING_APP + a.slice(src.length) : a);
    // ding.js starts with "#!/usr/bin/env gjs": the library would load into
    // env and be removed from the environment before gjs. gjs is launched
    // directly (the command line stays the same: "gjs .../ding.js ...").
    if (argv[0].endsWith('.js'))
        argv = ['gjs', ...argv];
    console.log(`Zorin XP: ícones do ambiente de trabalho: ${argv.join(' ')}${namesReady() ? ' (nomes do XP)' : ''}`);
    return argv;
}

export class DesktopNames {
    constructor() {
        this._timer = 0;
        // until the Zorin extension has launched the process
        if (!this._apply()) {
            this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, RETRY_MS, () => {
                if (!this._apply())
                    return GLib.SOURCE_CONTINUE;
                this._timer = 0;
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _process() {
        return Main.extensionManager.lookup(UUID)?.stateObj?.data?.currentProcess ?? null;
    }

    _apply() {
        const proc = this._process();
        if (!proc?.subprocess)
            return false;
        this._killStrays(proc);
        const proto = Object.getPrototypeOf(proc);
        if (!proto._zxpSpawnv) {
            proto._zxpSpawnv = proto.spawnv;
            proto.spawnv = function (argv) {
                return proto._zxpSpawnv.call(this, prepare(this, argv));
            };
        }
        // what is running was launched before this: relaunch it
        if (!proc._zxpPrepared)
            this._relaunch(proc);
        return true;
    }

    // The Zorin extension, when it starts, kills by program path the processes
    // left from before (e.g. Alt+F2 r): the copy's ones are killed here
    _killStrays(proc) {
        const mine = proc.subprocess.get_identifier();
        const prog = GLib.build_filenamev([DING_APP, 'ding.js']);
        try {
            const iter = Gio.File.new_for_path('/proc').enumerate_children(
                'standard::name', Gio.FileQueryInfoFlags.NONE, null);
            for (let info; (info = iter.next_file(null));) {
                const pid = info.get_name();
                if (/^\d+$/.test(pid) && pid !== mine && cmdline(pid)[1] === prog)
                    GLib.spawn_command_line_async(`kill ${pid}`);
            }
        } catch (e) {
            logError(e, 'Zorin XP: processos antigos do ambiente de trabalho');
        }
    }

    _relaunch(proc) {
        try {
            proc.subprocess?.force_exit();
        } catch (e) {
            logError(e, 'Zorin XP: relançar o ambiente de trabalho');
        }
    }

    // locked: the screen was locked (the extensions get disabled); everything
    // stays as it is, so the desktop does not flicker on every lock
    destroy(locked) {
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        if (locked)
            return;
        const proc = this._process();
        if (!proc)
            return;
        const proto = Object.getPrototypeOf(proc);
        if (!proto._zxpSpawnv)
            return;
        proto.spawnv = proto._zxpSpawnv;
        delete proto._zxpSpawnv;
        this._relaunch(proc);
    }
}
