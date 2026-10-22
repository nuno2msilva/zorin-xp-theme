// Zorin XP — botão "Desligar computador" do ecrã de boas-vindas (início de
// sessão e ecrã bloqueado), como no XP:
//   1. o diálogo "Desligar o computador" do menu Iniciar (xpDialog.js), com o
//      ecrã a perder a cor por trás;
//   2. com alguém com sessão iniciada, a caixa de aviso do user32 ("Janelas",
//      texto 713/714, Sim/Não) — arrastável pelo título, como qualquer janela;
//      enquanto pergunta, as contas e a ajuda desaparecem;
//   3. "O Windows está a encerrar..." com o som de encerrar, e só depois
//      desliga/reinicia.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {XpDialog, DLG_W, DLG_H, SHUTDOWN} from './xpDialog.js';

const GRAY_DELAY = 2000;      // como o diálogo do menu Iniciar (medido no XP)
const GRAY_TIME = 3000;
const SOUND_MAX_MS = 6000;

function loadJson(path) {
    try {
        return JSON.parse(new TextDecoder().decode(GLib.file_get_contents(path)[1]));
    } catch (e) {
        logError(e, `Zorin XP: ${path}`);
        return null;
    }
}

// toca um ficheiro de som e espera que acabe (no XP só desliga depois)
function playFile(path, maxMs) {
    return new Promise(resolve => {
        let done = false;
        const finish = () => {
            if (!done) {
                done = true;
                resolve();
            }
        };
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, maxMs, () => {
            finish();
            return GLib.SOURCE_REMOVE;
        });
        try {
            const proc = Gio.Subprocess.new(['canberra-gtk-play', '-f', path], Gio.SubprocessFlags.NONE);
            proc.wait_async(null, () => finish());
        } catch (e) {
            finish();
        }
    });
}

// Caixa de mensagem do user32 no estilo clássico (imagens de tools/builders/msgbox.py)
export class XpMessageBox {
    constructor(dir, kind, onAnswer) {
        const img = `${dir}/images`;
        const meta = loadJson(`${img}/msgbox.json`);
        if (!meta || !meta[kind])
            throw new Error('caixa de aviso sem imagens');
        const L = meta[kind];
        this._img = img;
        this._meta = meta;
        this._onAnswer = onAnswer;
        this._captionH = L.captionHeight;
        this.actor = new St.Widget({
            style: `background-image: url("${img}/msgbox-${kind}.png");`,
            width: L.width, height: L.height,
            reactive: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        this._buttons = {};
        ['yes', 'no'].forEach((key, i) => {
            const b = new St.Button({
                x: L.buttonsX + i * (L.buttonW + L.buttonGap), y: L.buttonsY,
                width: L.buttonW, height: L.buttonH,
                can_focus: true, reactive: true,
            });
            b.connect('notify::pressed', () => this._sync());
            b.connect('key-focus-in', () => this._sync());
            b.connect('clicked', () => this._answer(key === 'yes'));
            this.actor.add_child(b);
            this._buttons[key] = b;
        });
        this._focus = 'yes';         // MB_DEFBUTTON1
        this._sync();

        this.actor.connect('key-press-event', (_a, ev) => this._onKey(ev));
        this.actor.connect('button-press-event', (_a, ev) => this._onPress(ev));
    }

    _sync() {
        for (const [key, b] of Object.entries(this._buttons)) {
            if (b.has_key_focus())
                this._focus = key;
        }
        for (const [key, b] of Object.entries(this._buttons)) {
            const st = b.pressed ? 'pressed' : key === this._focus ? 'default' : 'normal';
            b.style = `background-image: url("${this._img}/msgbox-${key}-${st}.png");`;
        }
    }

    grabFocus() {
        this._buttons[this._focus].grab_key_focus();
        this._sync();
    }

    _onKey(ev) {
        const sym = ev.get_key_symbol();
        const ch = String.fromCodePoint(Clutter.keysym_to_unicode(sym) || 32).toLowerCase();
        if (ch === this._meta.yesKey || ch === this._meta.noKey) {
            this._answer(ch === this._meta.yesKey);
            return Clutter.EVENT_STOP;
        }
        if (sym === Clutter.KEY_Return || sym === Clutter.KEY_KP_Enter || sym === Clutter.KEY_space) {
            this._answer(this._focus === 'yes');
            return Clutter.EVENT_STOP;
        }
        if ([Clutter.KEY_Tab, Clutter.KEY_ISO_Left_Tab, Clutter.KEY_Left, Clutter.KEY_Right,
            Clutter.KEY_Up, Clutter.KEY_Down].includes(sym)) {
            this._focus = this._focus === 'yes' ? 'no' : 'yes';
            this.grabFocus();
            return Clutter.EVENT_STOP;
        }
        // (MB_YESNO: sem Esc nem fechar)
        return Clutter.EVENT_STOP;
    }

    // arrastar pelo título, como uma janela
    _onPress(ev) {
        if (ev.get_button() !== 1)
            return Clutter.EVENT_PROPAGATE;
        const [sx, sy] = ev.get_coords();
        const [ax, ay] = this.actor.get_transformed_position();
        if (sy - ay >= this._captionH)
            return Clutter.EVENT_STOP;
        const [px, py] = this.actor.get_position();
        this._dragId = global.stage.connect('captured-event', (_s, e) => {
            const t = e.type();
            if (t === Clutter.EventType.MOTION) {
                const [x, y] = e.get_coords();
                const parent = this.actor.get_parent();
                // (o título nunca sai do ecrã)
                const nx = Math.round(px + x - sx);
                const ny = Math.round(py + y - sy);
                this.actor.set_position(
                    Math.max(-this.actor.width + 40, Math.min(parent.width - 40, nx)),
                    Math.max(0, Math.min(parent.height - this._captionH, ny)));
                return Clutter.EVENT_STOP;
            }
            if (t === Clutter.EventType.BUTTON_RELEASE) {
                this._endDrag();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        return Clutter.EVENT_STOP;
    }

    _endDrag() {
        if (this._dragId)
            global.stage.disconnect(this._dragId);
        this._dragId = 0;
    }

    _answer(yes) {
        const cb = this._onAnswer;
        this._onAnswer = null;
        cb?.(yes);
    }

    destroy() {
        this._endDrag();
        this.actor.destroy();
    }
}

/*
 * parent: o diálogo de boas-vindas (ocupa o monitor); ui: XpWelcome;
 * opts.loggedIn(): há sessões iniciadas; opts.power(action): desliga/reinicia.
 */
export class TurnOff {
    constructor(parent, ui, dir, opts) {
        this._parent = parent;
        this._ui = ui;
        this._dir = dir;
        this._opts = opts;
    }

    get busy() {
        return !!this._blocker || this._shuttingDown;
    }

    open() {
        if (this.busy)
            return;
        // (modal: nada por trás responde enquanto o diálogo está aberto)
        this._blocker = new St.Widget({reactive: true, x: 0, y: 0,
            width: this._parent.width, height: this._parent.height});
        this._parent.add_child(this._blocker);
        this._dialog = new XpDialog(`${this._dir}/images`, this._ui.strings, SHUTDOWN,
            action => this._act(action));
        this._center(this._dialog.actor, DLG_W + 2, DLG_H + 2);
        this._parent.add_child(this._dialog.actor);
        this._dialog._cancel.grab_key_focus();
        this._startGray();
    }

    _center(actor, w, h) {
        actor.set_position(Math.floor((this._parent.width - w) / 2),
            Math.floor((this._parent.height - h) / 2));
    }

    _act(action) {
        this._dialog?.destroy();
        this._dialog = null;
        this._stopGray();
        if (action === 'cancel') {
            this._closeBlocker();
            return;
        }
        if (action === 'suspend') {
            this._closeBlocker();
            try {
                SystemActions.getDefault().activateSuspend();
            } catch (e) {
                logError(e, 'Zorin XP: suspender');
            }
            return;
        }
        if (!this._opts.loggedIn()) {
            this._proceed(action);
            return;
        }
        this._ui.setListHidden(true);
        this._box = new XpMessageBox(this._dir, action === 'restart' ? 'restart' : 'shutdown', yes => {
            this._box?.destroy();
            this._box = null;
            this._ui.setListHidden(false);
            if (yes)
                this._proceed(action);
            else
                this._closeBlocker();
        });
        this._center(this._box.actor, this._box.actor.width, this._box.actor.height);
        this._parent.add_child(this._box.actor);
        this._box.grabFocus();
    }

    async _proceed(action) {
        this._closeBlocker();
        this._shuttingDown = true;
        this._ui.showStatus(this._ui.strings.shuttingDown);
        await playFile(`${this._dir}/sounds/shutdown.wav`, SOUND_MAX_MS);
        this._opts.power(action);
    }

    _closeBlocker() {
        this._blocker?.destroy();
        this._blocker = null;
    }

    // ------------------------------------------- fundo a perder a cor
    _startGray() {
        this._stopGray();
        const target = this._ui.actor;
        this._desat = new Clutter.DesaturateEffect({factor: 0});
        this._dim = new Clutter.BrightnessContrastEffect();
        target.add_effect_with_name('zxp-desaturate', this._desat);
        target.add_effect_with_name('zxp-dim', this._dim);
        const start = GLib.get_monotonic_time() / 1000 + GRAY_DELAY;
        this._grayTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 40, () => {
            const t = (GLib.get_monotonic_time() / 1000 - start) / GRAY_TIME;
            if (t < 0)
                return GLib.SOURCE_CONTINUE;
            const k = Math.min(1, t);
            const eased = 1 - Math.pow(1 - k, 2);
            this._desat.factor = eased;
            this._dim.set_brightness(-0.04 * eased);
            if (k >= 1) {
                this._grayTimer = 0;
                return GLib.SOURCE_REMOVE;
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopGray() {
        if (this._grayTimer)
            GLib.source_remove(this._grayTimer);
        this._grayTimer = 0;
        this._ui.actor.remove_effect_by_name('zxp-desaturate');
        this._ui.actor.remove_effect_by_name('zxp-dim');
        this._desat = this._dim = null;
    }

    destroy() {
        this._stopGray();
        this._dialog?.destroy();
        this._box?.destroy();
        this._closeBlocker();
        this._dialog = this._box = null;
    }
}

// desligar/reiniciar pelo logind (o ecrã de início de sessão não tem sessão
// do utilizador para fechar)
export function login1Power(action) {
    const method = action === 'restart' ? 'Reboot' : 'PowerOff';
    // (os testes falam com o logind verdadeiro: nunca desligar a máquina)
    if (GLib.getenv('ZXP_LOGON_TEST')) {
        log(`Zorin XP: [teste] login1.${method}`);
        return;
    }
    Gio.DBus.system.call('org.freedesktop.login1', '/org/freedesktop/login1',
        'org.freedesktop.login1.Manager', method, new GLib.Variant('(b)', [true]), null,
        Gio.DBusCallFlags.NONE, -1, null, (conn, res) => {
            try {
                conn.call_finish(res);
            } catch (e) {
                logError(e, `Zorin XP: login1.${method}`);
            }
        });
}
