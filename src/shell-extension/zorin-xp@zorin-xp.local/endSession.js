/*
 * Turn Off Computer / Log Off as in XP.
 *
 * gnome-session asks the Shell for the end-session dialog over D-Bus
 * (EndSessionDialog.Open); instead of GNOME's dialog (with a 60 s countdown)
 * XP's opens — msgina.dll dialog 20100 and shell32.dll dialog 1089, with the
 * images and texts from those binaries — and the answer (ConfirmedShutdown,
 * ConfirmedReboot, ConfirmedLogout or Canceled) is given right on the click.
 *
 * While the dialog is open, the desktop slowly loses its colour (as in XP:
 * it starts ~2 s later and takes ~3 s, measured). On confirming, XP's status
 * screen appears with its sound, and only after the sound ends does the
 * session end.
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

// Start opens the dialog directly (without a round trip through gnome-session)
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

// last resort: logind turns off/restarts without going through gnome-session
function login1Call(method) {
    // (the test environment talks to the real logind: never turn the machine off)
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

// plays a theme sound and waits for it to end (in XP the session only ends after)
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
        // D-Bus methods are looked up on the object on every call
        dlg.OpenAsync = (params, invocation) => this._open(params, invocation);
        dlg.Close = () => this._close();
    }

    _open(params, invocation) {
        const [type] = params;
        // the Shell itself already confirmed (Shutdown()/Reboot() asked by Start):
        // gnome-session asks for the dialog as a formality — answer at once
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

    // request from the Shell itself (Start menu): no gnome-session dialog waiting
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

    // ------------------------------------------- background losing its colour
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
            const eased = 1 - Math.pow(1 - k, 2);  // faster at the start, as in XP
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

    // ------------------------------------------------------------ actions
    // answer to gnome-session: to the dialog it asked for, or, if the dialog
    // was opened by the Shell, a direct request without confirmation
    _emit(signal) {
        if (!this._local) {
            this._dlg?._dbusImpl.emit_signal(signal, null);
            return;
        }
        if (signal === 'ConfirmedLogout') {
            sessionManagerCall('Logout', new GLib.Variant('(u)', [1]));
            return;
        }
        // (gnome-session 46 no longer implements RequestShutdown/RequestReboot:
        // Shutdown()/Reboot() ask us for the dialog, which _open confirms at once)
        const reboot = signal === 'ConfirmedReboot';
        this._confirming = {type: reboot ? RESTART : SHUTDOWN, signal};
        const fallback = () => login1Call(reboot ? 'Reboot' : 'PowerOff');
        sessionManagerCall(reboot ? 'Reboot' : 'Shutdown', null, fallback);
        // if gnome-session does not go ahead (stuck application), the system does it
        this._fallbackId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 20, () => {
            this._fallbackId = 0;
            fallback();
            return GLib.SOURCE_REMOVE;
        });
    }

    // the lock screen (welcome screen extension) already asked and already
    // shows XP's status: only asking gnome-session is left
    requestPower(action) {
        this._local = true;
        this._emit(action === 'restart' ? 'ConfirmedReboot' : 'ConfirmedShutdown');
    }

    // XP: "Mudar de utilizador" (Switch User) locks the session and shows the
    // welcome screen, even with a single account (GNOME only allows it with several)
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
        // log off / turn off / restart: XP's status screen, sound, and only then
        // the confirmation (gnome-session ends everything after that)
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
