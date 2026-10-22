/*
 * Desligar o computador / Terminar sessão como no XP.
 *
 * O gnome-session pede ao Shell o diálogo de fim de sessão por D-Bus
 * (EndSessionDialog.Open); em vez do diálogo do GNOME (com contagem de 60 s)
 * abre-se o do XP — msgina.dll diálogo 20100 e shell32.dll diálogo 1089,
 * com as imagens e textos desses binários — e a resposta (ConfirmedShutdown,
 * ConfirmedReboot, ConfirmedLogout ou Canceled) é dada logo ao clicar.
 *
 * Enquanto o diálogo está aberto, o ambiente de trabalho perde a cor aos
 * poucos (como no XP: começa ~2 s depois e demora ~3 s, medido). Ao
 * confirmar aparece o ecrã de estado do XP com o som respetivo, e só depois
 * do som acabar é que a sessão termina.
 */
import Clutter from 'gi://Clutter';
import Gdm from 'gi://Gdm';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {XpScreen, xpStrings} from './xpScreen.js';
import {closeStartMenus} from './startmenu.js';

import {LOGOUT, SHUTDOWN, RESTART, DLG_W, DLG_H, XpDialog} from './xpDialog.js';

export {LOGOUT, SHUTDOWN, RESTART, XpDialog};

let _instance = null;

// o Iniciar abre o diálogo diretamente (sem ir e voltar pelo gnome-session)
export function showEndSession(type) {
    if (!_instance)
        return false;
    _instance.showLocal(type);
    return true;
}

function sessionManagerCall(method, params = null, onError = null) {
    Gio.DBus.session.call('org.gnome.SessionManager', '/org/gnome/SessionManager',
        'org.gnome.SessionManager', method, params, null, Gio.DBusCallFlags.NONE, -1, null,
        (conn, res) => {
            try {
                conn.call_finish(res);
            } catch (e) {
                logError(e, `Zorin XP: SessionManager.${method}`);
                onError?.();
            }
        });
}

// último recurso: o logind desliga/reinicia sem passar pelo gnome-session
function login1Call(method) {
    // (o ambiente de testes fala com o logind verdadeiro: nunca desligar a máquina)
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

const GRAY_DELAY = 2000;
const GRAY_TIME = 3000;

function sleep(ms) {
    return new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
}

// toca um som do tema e espera que acabe (no XP a sessão só termina depois)
export function playAndWait(id, maxMs) {
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
            const proc = Gio.Subprocess.new(['canberra-gtk-play', '-i', id], Gio.SubprocessFlags.NONE);
            proc.wait_async(null, () => finish());
        } catch (e) {
            global.display.get_sound_player().play_from_theme(id, id, null);
        }
    });
}

export function playSound(id) {
    global.display.get_sound_player().play_from_theme(id, id, null);
}

export class EndSession {
    constructor(ext) {
        this._ext = ext;
        _instance = this;
        const dlg = Main.endSessionDialog;
        if (!dlg)
            return;
        this._dlg = dlg;
        // os métodos D-Bus são procurados no objeto a cada chamada
        dlg.OpenAsync = (params, invocation) => this._open(params, invocation);
        dlg.Close = () => this._close();
    }

    _open(params, invocation) {
        const [type] = params;
        // o próprio Shell já confirmou (Shutdown()/Reboot() pedidos pelo Iniciar):
        // o gnome-session pede o diálogo por formalidade — responde-se logo
        if (this._confirming && this._confirming.type === type) {
            invocation.return_value(null);
            const signal = this._confirming.signal;
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                this._dlg?._dbusImpl.emit_signal(signal, null);
                return GLib.SOURCE_REMOVE;
            });
            return undefined;
        }
        if (![LOGOUT, SHUTDOWN, RESTART].includes(type) || this._busy) {
            return Object.getPrototypeOf(this._dlg).OpenAsync.call(this._dlg, params, invocation);
        }
        try {
            this._show(type);
            invocation.return_value(null);
        } catch (e) {
            logError(e, 'Zorin XP: diálogo de fim de sessão');
            this._close();
            return Object.getPrototypeOf(this._dlg).OpenAsync.call(this._dlg, params, invocation);
        }
        return undefined;
    }

    // pedido do próprio Shell (menu Iniciar): sem diálogo do gnome-session à espera
    showLocal(type) {
        if (this._busy)
            return;
        this._show(type);
        this._local = true;
    }

    _show(type) {
        this._close();
        this._local = false;
        closeStartMenus();
        this._dialog = new XpDialog(`${this._ext.path}/logon/images`, xpStrings(this._ext.path), type,
            action => this._act(action));
        const mon = Main.layoutManager.primaryMonitor;
        this._dialog.actor.set_position(
            mon.x + Math.floor((mon.width - DLG_W - 2) / 2),
            mon.y + Math.floor((mon.height - DLG_H - 2) / 2));
        global.stage.add_child(this._dialog.actor);
        global.stage.set_child_above_sibling(this._dialog.actor, null);
        this._grab = Main.pushModal(this._dialog.actor, {actionMode: Shell.ActionMode.SYSTEM_MODAL});
        this._dialog._cancel.grab_key_focus();
        this._startGray();
    }

    // ------------------------------------------- fundo a perder a cor
    _startGray() {
        this._stopGray();
        const ui = Main.layoutManager.uiGroup;
        this._desat = new Clutter.DesaturateEffect({factor: 0});
        this._dim = new Clutter.BrightnessContrastEffect();
        ui.add_effect_with_name('zxp-desaturate', this._desat);
        ui.add_effect_with_name('zxp-dim', this._dim);
        const start = GLib.get_monotonic_time() / 1000 + GRAY_DELAY;
        this._grayTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 40, () => {
            const t = (GLib.get_monotonic_time() / 1000 - start) / GRAY_TIME;
            if (t < 0)
                return GLib.SOURCE_CONTINUE;
            const k = Math.min(1, t);
            const eased = 1 - Math.pow(1 - k, 2);  // mais rápido no início, como no XP
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
        const ui = Main.layoutManager.uiGroup;
        ui.remove_effect_by_name('zxp-desaturate');
        ui.remove_effect_by_name('zxp-dim');
        this._desat = this._dim = null;
    }

    _close() {
        if (this._grab)
            Main.popModal(this._grab);
        this._grab = null;
        this._dialog?.destroy();
        this._dialog = null;
    }

    // ------------------------------------------------------------ ações
    // resposta ao gnome-session: ao diálogo que ele pediu, ou, se o diálogo foi
    // aberto pelo Shell, pedido direto sem confirmação
    _emit(signal) {
        if (!this._local) {
            this._dlg?._dbusImpl.emit_signal(signal, null);
            return;
        }
        if (signal === 'ConfirmedLogout') {
            sessionManagerCall('Logout', new GLib.Variant('(u)', [1]));
            return;
        }
        // (o gnome-session 46 já não implementa RequestShutdown/RequestReboot:
        // Shutdown()/Reboot() pedem-nos o diálogo, que _open confirma logo)
        const reboot = signal === 'ConfirmedReboot';
        this._confirming = {type: reboot ? RESTART : SHUTDOWN, signal};
        const fallback = () => login1Call(reboot ? 'Reboot' : 'PowerOff');
        sessionManagerCall(reboot ? 'Reboot' : 'Shutdown', null, fallback);
        // se o gnome-session não avançar (aplicação presa), o sistema faz-o
        this._fallbackId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 20, () => {
            this._fallbackId = 0;
            fallback();
            return GLib.SOURCE_REMOVE;
        });
    }

    // o ecrã bloqueado (extensão do ecrã de boas-vindas) já perguntou e já
    // mostra o estado do XP: só falta pedir ao gnome-session
    requestPower(action) {
        this._local = true;
        this._emit(action === 'restart' ? 'ConfirmedReboot' : 'ConfirmedShutdown');
    }

    // XP: "Mudar de utilizador" bloqueia a sessão e mostra o ecrã de boas-vindas,
    // mesmo com uma só conta (o GNOME só o permite com várias)
    _switchUser() {
        Main.screenShield?.lock(false);
        Clutter.threads_add_repaint_func_full(Clutter.RepaintFlags.POST_PAINT, () => {
            try {
                Gdm.goto_login_session_sync(null);
            } catch (e) {
                logError(e, 'Zorin XP: mudar de utilizador');
            }
            return false;
        });
    }

    async _act(action) {
        this._close();
        if (action === 'cancel') {
            this._stopGray();
            this._emit('Canceled');
            this._emit('Closed');
            return;
        }
        if (action === 'switch-user' || action === 'suspend') {
            this._stopGray();
            this._emit('Canceled');
            this._emit('Closed');
            if (action === 'switch-user') {
                this._switchUser();
            } else {
                try {
                    SystemActions.getDefault().activateSuspend();
                } catch (e) {
                    logError(e, 'Zorin XP: suspender');
                }
            }
            return;
        }
        // terminar sessão / desligar / reiniciar: ecrã de estado do XP, som,
        // e só então a confirmação (o gnome-session termina tudo a seguir)
        this._busy = true;
        const s = xpStrings(this._ext.path);
        const screen = new XpScreen(this._ext.path);
        screen.showStatus(s.loggingOff);
        this._stopGray();
        try {
            if (action === 'logout') {
                await playAndWait('desktop-logout', 4000);
                screen.setStatus(s.savingSettings);
                await sleep(600);
                screen.setStatus(s.closingNetwork);
                await sleep(400);
                this._emit('ConfirmedLogout');
            } else {
                screen.setStatus(s.savingSettings);
                await playAndWait('system-shutdown', 5000);
                screen.setStatus(s.shuttingDown);
                await sleep(300);
                this._emit(action === 'restart' ? 'ConfirmedReboot' : 'ConfirmedShutdown');
            }
        } catch (e) {
            logError(e, 'Zorin XP: fim de sessão');
            screen.destroy();
            this._busy = false;
        }
    }

    destroy() {
        if (_instance === this)
            _instance = null;
        this._close();
        this._stopGray();
        if (this._dlg) {
            delete this._dlg.OpenAsync;
            delete this._dlg.Close;
        }
        this._dlg = null;
    }
}
