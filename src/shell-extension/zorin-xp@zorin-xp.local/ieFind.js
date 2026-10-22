/*
 * A janela Localizar do "Internet Explorer" (o Zen, src/zen-ie/find): fica
 * pronta, minimizada, de uma vez para a outra. Como um diálogo do IE, não tem
 * botão na barra de tarefas nem aparece no Alt+Tab ou na vista geral, e abre
 * e fecha sem animação.
 *
 * O título é o que a distingue ("Extension: (Localizar) - Localizar — ...").
 * O Shell não tem maneira de pôr skip_taskbar pelo JS: no X11 pede-se como as
 * aplicações pedem (skiptaskbar.py).
 */
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const TITLE = /\(Localizar\) - Localizar/;

function isZen(w) {
    return [w.get_wm_class(), w.get_wm_class_instance(), w.get_sandboxed_app_id()]
        .some(s => /zen/i.test(s || ''));
}

export class IeFind {
    constructor(path) {
        this._helper = GLib.build_filenamev([path, 'skiptaskbar.py']);
        this._windows = new Map();     // janela -> [ligações]
        this._find = new WeakSet();    // as janelas Localizar
        const wm = Main.wm;
        this._shouldAnimate = wm._shouldAnimateActor;
        const self = this;
        wm._shouldAnimateActor = function (actor, types) {
            if (actor.meta_window && self._find.has(actor.meta_window))
                return false;
            return self._shouldAnimate.call(this, actor, types);
        };
        this._createdId = global.display.connect('window-created', (_d, w) => this._track(w));
        for (const actor of global.get_window_actors())
            this._track(actor.meta_window);
    }

    _track(w) {
        if (!w || this._windows.has(w))
            return;
        const ids = [];
        this._windows.set(w, ids);
        ids.push(w.connect('notify::title', () => this._check(w)));
        ids.push(w.connect('unmanaged', () => this._untrack(w)));
        this._check(w);
    }

    _check(w) {
        if (this._find.has(w) || !TITLE.test(w.get_title() || '') || !isZen(w))
            return;
        this._find.add(w);
        if (Meta.is_wayland_compositor() || w.get_client_type() !== Meta.WindowClientType.X11)
            return;
        const xid = w.get_description();      // ("0x...": a janela X11)
        if (!/^0x[0-9a-f]+$/i.test(xid))
            return;
        try {
            const proc = Gio.Subprocess.new(['python3', this._helper, xid], Gio.SubprocessFlags.NONE);
            proc.wait_async(null, () => {
                // (a zorin-taskbar só volta a filtrar quando a aplicação muda de janelas)
                const app = Shell.WindowTracker.get_default().get_window_app(w);
                app?.emit('windows-changed');
            });
        } catch (e) {
            console.warn(`Zorin XP: Localizar fora da barra de tarefas: ${e.message}`);
        }
    }

    _untrack(w) {
        for (const id of this._windows.get(w) || [])
            w.disconnect(id);
        this._windows.delete(w);
    }

    destroy() {
        global.display.disconnect(this._createdId);
        for (const w of [...this._windows.keys()])
            this._untrack(w);
        Main.wm._shouldAnimateActor = this._shouldAnimate;
    }
}
