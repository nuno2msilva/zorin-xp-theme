/*
 * Ícones do ambiente de trabalho como no XP:
 *  - "O meu computador" e "Reciclagem" em vez de "Pasta pessoal" e "Lixo";
 *  - a grelha do XP (células mais pequenas).
 *
 * Os ícones são desenhados por um processo gjs à parte, que a extensão
 * zorin-desktop-icons lança com um Gio.SubprocessLauncher. Junta-se a esse
 * lançador a biblioteca zorin-xp-gettext.so (LD_PRELOAD), que faz o processo
 * usar as traduções de ~/.local/share/zorin-xp/locale (tools/setup/molocale.py), e
 * troca-se o programa pela cópia com a grelha do XP (tools/setup/dingcopy.py), se
 * ainda corresponder aos ficheiros do Zorin. Depois relança-se o processo (a
 * extensão do Zorin volta a lançá-lo sozinha). Nada do sistema se mexe.
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

// A cópia só vale se os ficheiros do Zorin forem os mesmos de quando foi feita
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
    // O ding.js começa por "#!/usr/bin/env gjs": a biblioteca carregava-se no
    // env e tirava-se do ambiente antes do gjs. Lança-se o gjs diretamente
    // (a linha de comando fica a mesma: "gjs .../ding.js ...").
    if (argv[0].endsWith('.js'))
        argv = ['gjs', ...argv];
    console.log(`Zorin XP: ícones do ambiente de trabalho: ${argv.join(' ')}${namesReady() ? ' (nomes do XP)' : ''}`);
    return argv;
}

export class DesktopNames {
    constructor() {
        this._timer = 0;
        // até a extensão do Zorin ter lançado o processo
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
        // o que está a correr foi lançado antes disto: relança-se
        if (!proc._zxpPrepared)
            this._relaunch(proc);
        return true;
    }

    // A extensão do Zorin, ao arrancar, mata pelo caminho do programa os
    // processos que ficaram de antes (ex. Alt+F2 r): os da cópia matam-se aqui
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

    // locked: o ecrã foi bloqueado (as extensões desligam-se); fica tudo como
    // está, para o ambiente de trabalho não piscar a cada bloqueio
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
