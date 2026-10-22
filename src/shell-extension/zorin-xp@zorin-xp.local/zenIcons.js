/*
 * O Zen (o "Internet Explorer") com o ícone da página aberta na legenda da
 * janela e no botão da barra de tarefas, em vez do ícone da aplicação.
 *
 * A extensão do Zen src/zen-ie/title guarda, para cada janela, o favicon da
 * página escolhida (16 px; sem favicon, a página do IE) numa pasta da cache
 * do Flatpak, com um index.json "título da janela -> ficheiro". Aqui lê-se esse
 * índice (com um monitor da pasta) e procura-se cada janela do Zen pelo
 * título; a legenda vem do frames.js (setIcon) e o botão como os do
 * Explorador (explorerIcons.js).
 */
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {setButtonIcon, restoreButtonIcon, taskbarButtons} from './explorerIcons.js';

const WM_CLASS = 'zen';
// (o Zen em Flatpak escreve na cache dele; um Zen fora do Flatpak, na ~/.cache)
const DIRS = [
    GLib.build_filenamev([GLib.get_home_dir(), '.var', 'app', 'app.zen_browser.zen', 'cache', 'zorin-xp-favicons']),
    GLib.build_filenamev([GLib.get_user_cache_dir(), 'zorin-xp-favicons']),
];

export class ZenIcons {
    constructor(ext) {
        this._ext = ext;
        this._index = new Map();       // título -> caminho do ícone
        this._windows = new Set();
        this._buttons = new Set();
        this._timer = 0;
        this._monitors = [];
        for (const dir of DIRS) {
            const file = Gio.File.new_for_path(dir);
            try {
                const monitor = file.monitor_directory(Gio.FileMonitorFlags.NONE, null);
                monitor.connect('changed', () => this._soon());
                this._monitors.push(monitor);
            } catch (e) {}
        }
        global.display.connectObject('window-created', (_d, w) => {
            this._track(w);
            this._soon();
        }, this);
        for (const actor of global.get_window_actors())
            this._track(actor.meta_window);
        this._load();
    }

    _track(w) {
        if (this._windows.has(w))
            return;
        this._windows.add(w);
        w.connectObject(
            'notify::title', () => this._apply(w),
            'notify::wm-class', () => this._apply(w),
            'unmanaged', () => {
                w.disconnectObject(this);
                this._windows.delete(w);
            }, this);
    }

    // (o índice muda várias vezes seguidas; o botão de uma janela nova
    // aparece pouco depois da janela)
    _soon() {
        if (this._timer)
            return;
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            this._timer = 0;
            this._load();
            return GLib.SOURCE_REMOVE;
        });
    }

    _load() {
        this._index.clear();
        for (const dir of DIRS) {
            try {
                const [, data] = GLib.file_get_contents(GLib.build_filenamev([dir, 'index.json']));
                for (const [title, name] of Object.entries(JSON.parse(new TextDecoder().decode(data))))
                    this._index.set(title, GLib.build_filenamev([dir, name]));
            } catch (e) {}
        }
        for (const w of this._windows)
            this._apply(w);
    }

    _iconFor(w) {
        if (w.get_wm_class() !== WM_CLASS)
            return null;
        const path = this._index.get(w.get_title() ?? '');
        return path && GLib.file_test(path, GLib.FileTest.EXISTS)
            ? Gio.FileIcon.new(Gio.File.new_for_path(path)) : null;
    }

    _apply(w) {
        const gicon = this._iconFor(w);
        this._ext._frames?.setIcon(w, gicon);
        for (const button of taskbarButtons()) {
            if (button.window !== w)
                continue;
            if (gicon) {
                if (setButtonIcon(button, gicon))
                    this._buttons.add(button);
            } else if (this._buttons.delete(button)) {
                restoreButtonIcon(button);
            }
        }
    }

    destroy() {
        if (this._timer)
            GLib.source_remove(this._timer);
        for (const monitor of this._monitors)
            monitor.cancel();
        this._monitors = [];
        global.display.disconnectObject(this);
        for (const w of this._windows) {
            w.disconnectObject(this);
            this._ext._frames?.setIcon(w, null);
        }
        this._windows.clear();
        for (const button of this._buttons)
            restoreButtonIcon(button);
        this._buttons.clear();
    }
}
