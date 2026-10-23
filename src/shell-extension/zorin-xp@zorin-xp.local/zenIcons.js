/*
 * Zen (the "Internet Explorer") with the open page's icon in the window
 * caption and on the taskbar button, instead of the application's icon.
 *
 * The Zen extension src/zen-ie/title saves, for each window, the favicon of
 * the selected page (16 px; without a favicon, IE's page) in a folder of the
 * Flatpak's cache, with an index.json "window title -> file". Here that
 * index is read (with a folder monitor) and each Zen window is looked up by
 * its title; the caption comes from frames.js (setIcon) and the button like
 * the Explorer's (explorerIcons.js).
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
        this._index = new Map();       // title -> icon path
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

    // (the index changes several times in a row; a new window's button appears
    // shortly after the window)
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
