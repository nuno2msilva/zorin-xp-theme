// Zorin XP — the login screen (GDM) is XP's welcome screen.
//
// GNOME Shell in gdm mode creates the dialog given in
// Main.sessionMode.unlockDialog; the extension puts this class there, so
// GNOME's dialog never exists. Authentication uses GNOME's verifier
// (auth.js) and the session start GDM's greeter, like the original.

import AccountsService from 'gi://AccountsService';
import Clutter from 'gi://Clutter';
import Gdm from 'gi://Gdm';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Layout from 'resource:///org/gnome/shell/ui/layout.js';
import * as LoginManager from 'resource:///org/gnome/shell/misc/loginManager.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {XpAuth} from './auth.js';
import {TurnOff, login1Power} from './turnOff.js';
import {XpWelcome} from './welcome.js';

const BOOT_STATUS_MS = 1500;   // "O Windows está a iniciar..." right after boot

export function listUsers(userManager) {
    return userManager.list_users()
        .filter(u => u.is_loaded && !u.is_system_account() && !u.locked && u.get_user_name())
        .sort((a, b) => (a.get_real_name() || a.get_user_name())
            .localeCompare(b.get_real_name() || b.get_user_name()));
}

export function userInfo(u) {
    return {
        name: u.get_user_name(),
        realName: u.get_real_name(),
        iconFile: u.get_icon_file(),
        loggedIn: u.is_logged_in(),
    };
}

export function uptime() {
    try {
        return parseFloat(new TextDecoder().decode(GLib.file_get_contents('/proc/uptime')[1]));
    } catch (e) {
        return 1e9;
    }
}

export const XpLoginDialog = GObject.registerClass({
    Signals: {'failed': {}, 'wake-up-screen': {}},
}, class XpLoginDialog extends St.Widget {
    _init(parentActor, ext) {
        super._init({style_class: 'zxp-logon', visible: false, reactive: true});
        this._ext = ext;
        this.add_constraint(new Layout.MonitorConstraint({primary: true}));
        parentActor.add_child(this);
        this.connect('destroy', () => this._onDestroy());
        this.connect('key-press-event', (_a, ev) =>
            this._guard(() => this._ui.handleListKey(ev)) ? Clutter.EVENT_STOP : Clutter.EVENT_PROPAGATE);

        this._ui = new XpWelcome(ext.path);
        this.add_child(this._ui.actor);
        this._ui.onUserClicked = name => this._guard(() => this._select(name));
        this._ui.onSubmit = text => this._guard(() => this._submit(text));
        this._ui.onCancel = () => this._guard(() => this._cancelUser());
        this._ui.onDeselect = () => this._guard(() => this._cancelUser());
        this._ui.onTurnOff = () => this._guard(() => this._turnOff());
        this._ui.relayout();
        Main.layoutManager.connectObject('monitors-changed', () => this._ui.relayout(), this);

        this._userManager = AccountsService.UserManager.get_default();
        this._gdmClient = new Gdm.Client();
        try {
            this._gdmClient.set_enabled_extensions([
                Gdm.UserVerifierChoiceList.interface_info().name,
                Gdm.UserVerifierCustomJSON.interface_info().name,
            ]);
        } catch (e) {}
        this._newAuth();
        this._resetGreeterProxy();
        this._watchGreeterSession().catch(logError);

        // right after boot: "O Windows está a iniciar..." until the accounts load
        this._booting = uptime() < 180;
        if (this._booting) {
            this._ui.showStatus(this._ui.strings.starting);
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, BOOT_STATUS_MS, () => {
                this._booting = false;
                this._guard(() => this._syncUsers());
                return GLib.SOURCE_REMOVE;
            });
        }
        this._userManager.connectObject(
            'notify::is-loaded', () => this._guard(() => this._syncUsers()),
            'user-added', () => this._guard(() => this._syncUsers()),
            'user-removed', () => this._guard(() => this._syncUsers()),
            'user-changed', () => this._guard(() => this._syncUsers()), this);
        this._syncUsers();
    }

    // an error in any reaction hands the screen back to GNOME (never be left unable to log in)
    _guard(fn) {
        try {
            return fn();
        } catch (e) {
            this._ext.fallback(this, e);
            return undefined;
        }
    }

    _newAuth() {
        this._auth?.destroy();
        this._auth = new XpAuth(this._gdmClient, false);
        this._auth.connect('question', (_a, question, secret) => this._guard(() => {
            this._ui.showPrompt(question, secret);
        }));
        this._auth.connect('failed', (_a, canRetry) => this._guard(() => {
            this._ui.entry.set_text('');
            if (canRetry)
                this._ui.showBalloon();
        }));
        this._auth.connect('complete', () => this._guard(() => {
            this._ui.showWelcome(this._ui.strings.loggingOn);
        }));
        this._auth.connect('reset', () => this._guard(() => this._onAuthReset()));
    }

    _syncUsers() {
        if (!this._userManager.is_loaded || this._booting)
            return;
        const users = listUsers(this._userManager);
        // no accounts to show (or the list is disabled): GNOME's screen stays
        if (users.length === 0)
            throw new Error('sem contas para o ecrã de boas-vindas');
        this._ui.showStatus(null);
        this._ui.setUsers(users.map(userInfo));
    }

    _select(name) {
        if (this._auth.complete || this._ui.selected === name)
            return;
        if (this._ui.selected)
            this._auth.cancel();
        this._ui.select(name);
        this._resetGreeterProxy();
        this._auth.begin(name);
    }

    _submit(text) {
        this._ui.setBusy(true);
        this._auth.answer(text);
    }

    _cancelUser() {
        // XP: Esc or a click on the background go back to the list, with no account selected
        if (this._auth.complete || !this._ui.selected)
            return;
        this._auth.cancel();
        this._ui.select(null);
        // (the arrows move through the list again)
        super.grab_key_focus();
    }

    _onAuthReset() {
        if (this._auth.complete)
            return;
        // if GDM does not answer and this loops, GNOME's screen stays
        const now = GLib.get_monotonic_time();
        this._resets = (this._resets ?? []).filter(t => now - t < 5e6);
        this._resets.push(now);
        if (this._resets.length > 3)
            throw new Error('o verificador do GDM não responde');
        // the verifier gave up (too many attempts) or was cancelled: back to the list
        this._ui.select(null);
    }

    _turnOff() {
        this._turnOffFlow ??= new TurnOff(this, this._ui, this._ext.path, {
            // XP: warns if anyone has a session open
            loggedIn: () => this._userManager.list_users().some(u =>
                u.is_loaded && !u.is_system_account() && u.is_logged_in()),
            power: action => login1Power(action),
        });
        this._turnOffFlow.open();
    }

    // ---------------------------------------------------------- greeter (GDM)
    _resetGreeterProxy() {
        if (GLib.getenv('GDM_GREETER_TEST') === '1')
            return;
        this._greeter?.disconnectObject(this);
        this._greeter?.run_dispose();
        this._greeter = this._gdmClient.get_greeter_sync(null);
        this._greeter.connectObject('session-opened',
            (_g, serviceName) => this._guard(() => this._onSessionOpened(serviceName)), this);
    }

    // runs fn after the next frame has really been drawn (or after 1 s)
    _afterPaint(fn, extraMs = 100) {
        let done = false;
        const run = () => {
            if (done)
                return;
            done = true;
            fn();
        };
        const id = global.stage.connect('after-paint', () => {
            global.stage.disconnect(id);
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, extraMs, () => {
                run();
                return GLib.SOURCE_REMOVE;
            });
        });
        global.stage.queue_redraw();
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
            run();
            return GLib.SOURCE_REMOVE;
        });
    }

    _onSessionOpened(serviceName) {
        // XP: "bem-vindo" on the screen before moving to the session (it is the
        // image that stays visible while the session's display server starts)
        this._ui.showWelcome(this._ui.strings.loggingOn);
        this._auth.finish(() => this._afterPaint(() => {
            log('Zorin XP: [sessão] a iniciar a sessão');
            this._greeter.call_start_session_when_ready_sync(serviceName, true, null);
        }, 300));
    }

    // the welcome screen becomes active again (switch user, log off)
    async _watchGreeterSession() {
        const proxy = await LoginManager.getLoginManager().getCurrentSessionProxy();
        this._greeterSession = proxy;
        proxy?.connectObject('g-properties-changed', (p, props) => {
            if (props.lookup_value('Active', null) && p.Active)
                this._guard(() => this._reactivated());
        }, this);
    }

    _reactivated() {
        if (this._auth.complete)
            return;
        this._auth.cancel();
        this._ui.select(null);
        this._syncUsers();
    }

    // -------------------------------------------- what ScreenShield uses
    // (ScreenShield gives the focus to the dialog: it goes to the password box)
    grab_key_focus() {
        if (this._ui.entry.mapped && this._ui.entry.reactive)
            this._ui.entry.grab_key_focus();
        else
            super.grab_key_focus();
    }

    open() {
        this.show();
        this._grab = Main.pushModal(global.stage, {actionMode: Shell.ActionMode.LOGIN_SCREEN});
        if (this._ui.selected && this._ui.entry.reactive)
            this._ui.entry.grab_key_focus();
        else
            super.grab_key_focus();     // (as setas escolhem a conta)
        log('Zorin XP: [arranque] ecrã de boas-vindas aberto');
        // already drawn underneath: the boot cover (identical to this one) can leave
        this._afterPaint(() => this._ext.coverDone());
        return true;
    }

    activate() {
        this.show();
    }

    close() {
        if (this._grab)
            Main.popModal(this._grab);
        this._grab = null;
    }

    popModal() {
        this.close();
    }

    cancel() {
        this._cancelUser();
    }

    addCharacter(_unichar) {
        // like GNOME: nothing is typed before choosing the account
    }

    finish(onComplete) {
        this._auth.finish(onComplete);
    }

    _onDestroy() {
        this.close();
        this._greeter?.disconnectObject(this);
        this._greeterSession?.disconnectObject(this);
        this._userManager.disconnectObject(this);
        Main.layoutManager.disconnectObject(this);
        this._turnOffFlow?.destroy();
        this._auth?.destroy();
        this._auth = null;
        this._ui.destroy();
    }
});
