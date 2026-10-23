// Zorin XP — the lock screen (Win+L, switch user) is XP's welcome screen, as
// in XP with fast user switching.
//
// Replaces GNOME's UnlockDialog (Main.sessionMode.unlockDialog): as in XP, it
// opens with the account list and none selected; clicking the account with
// the locked session shows the password box (Esc or a click on the background
// go back to the list) and clicking another account moves to the login
// screen (GDM). The check is GDM's reauthentication (auth.js); when it
// accepts, GDM unlocks the session (logind's Unlock signal) and ScreenShield
// closes this dialog.

import AccountsService from 'gi://AccountsService';
import Clutter from 'gi://Clutter';
import Gdm from 'gi://Gdm';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Layout from 'resource:///org/gnome/shell/ui/layout.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {XpAuth} from './auth.js';
import {TurnOff, login1Power} from './turnOff.js';
import {XpWelcome} from './welcome.js';
import {listUsers, userInfo} from './loginDialog.js';

export const XpUnlockDialog = GObject.registerClass({
    Signals: {'failed': {}, 'wake-up-screen': {}},
}, class XpUnlockDialog extends St.Widget {
    _init(parentActor, ext) {
        super._init({style_class: 'zxp-logon', visible: false, reactive: true});
        this._ext = ext;
        this.allowCancel = false;
        this.add_constraint(new Layout.MonitorConstraint({primary: true}));
        parentActor.add_child(this);
        this.connect('destroy', () => this._onDestroy());
        this.connect('key-press-event', (_a, ev) =>
            this._guard(() => this._ui.handleListKey(ev)) ? Clutter.EVENT_STOP : Clutter.EVENT_PROPAGATE);

        this._ui = new XpWelcome(ext.path);
        this.add_child(this._ui.actor);
        this._ui.onUserClicked = name => this._guard(() => this._select(name));
        this._ui.onSubmit = text => this._guard(() => this._auth?.answer(text));
        this._ui.onCancel = () => this._guard(() => this._deselect());
        this._ui.onDeselect = () => this._guard(() => this._deselect());
        this._ui.onTurnOff = () => this._guard(() => {
            this._turnOffFlow ??= new TurnOff(this, this._ui, ext.path, {
                loggedIn: () => true,        // the session itself is logged in
                power: action => {
                    // through gnome-session (applications close properly), via the session
                    // extension; otherwise, through logind
                    const es = Main.extensionManager.lookup('zorin-xp@zorin-xp.local')?.stateObj?._endSession;
                    if (es?.requestPower)
                        es.requestPower(action);
                    else
                        login1Power(action);
                },
            });
            this._turnOffFlow.open();
        });
        this._ui.relayout();
        Main.layoutManager.connectObject('monitors-changed', () => this._ui.relayout(), this);

        this._userName = GLib.get_user_name();
        this._userManager = AccountsService.UserManager.get_default();
        this._gdmClient = new Gdm.Client();
        try {
            this._gdmClient.set_enabled_extensions([
                Gdm.UserVerifierChoiceList.interface_info().name,
                Gdm.UserVerifierCustomJSON.interface_info().name,
            ]);
        } catch (e) {}

        this._userManager.connectObject(
            'notify::is-loaded', () => this._guard(() => this._syncUsers()),
            'user-added', () => this._guard(() => this._syncUsers()),
            'user-removed', () => this._guard(() => this._syncUsers()),
            'user-changed', () => this._guard(() => this._syncUsers()), this);
        this._syncUsers();

        // any key or movement wakes the screen (if it has dimmed)
        this.connect('captured-event', (_a, ev) => {
            const t = ev.type();
            if (t === Clutter.EventType.KEY_PRESS || t === Clutter.EventType.MOTION ||
                t === Clutter.EventType.BUTTON_PRESS)
                this.emit('wake-up-screen');
            return Clutter.EVENT_PROPAGATE;
        });
    }

    _guard(fn) {
        try {
            return fn();
        } catch (e) {
            this._ext.fallback(this, e);
            return undefined;
        }
    }

    _syncUsers() {
        let users = this._userManager.is_loaded ? listUsers(this._userManager) : [];
        // one's own account always shows, even before AccountsService loads
        if (!users.some(u => u.get_user_name() === this._userName)) {
            const me = this._userManager.get_user(this._userName);
            users = [me, ...users];
        }
        this._ui.setUsers(users.map(u => u.is_loaded ? userInfo(u) : {
            name: this._userName, realName: GLib.get_real_name(), iconFile: null, loggedIn: true,
        }));
    }

    _select(name) {
        if (name !== this._userName) {
            // another account: GDM's login screen (switch user)
            try {
                Gdm.goto_login_session_sync(null);
            } catch (e) {
                logError(e, 'Zorin XP: mudar de utilizador');
            }
            return;
        }
        if (this._ui.selected === name && this._auth)
            return;
        this._ui.select(name);
        this._begin();
    }

    _deselect() {
        if (!this._ui.selected)
            return;
        this._auth?.destroy();
        this._auth = null;
        this._pending = null;
        this._ui.select(null);
        // (the arrows move through the list again)
        super.grab_key_focus();
    }

    _begin() {
        this._auth?.destroy();
        this._auth = new XpAuth(this._gdmClient, true);
        this._auth.connect('question', (_a, question, secret) => this._guard(() => {
            this._ui.showPrompt(question, secret);
            if (this._pending) {
                this._ui.entry.clutter_text.insert_text(this._pending, -1);
                this._pending = null;
            }
        }));
        this._auth.connect('failed', () => this._guard(() => {
            this._ui.entry.set_text('');
            this._ui.showBalloon();
        }));
        this._auth.connect('reset', () => this._guard(() => {
            // start over; if GDM does not answer and this loops, GNOME stays
            const now = GLib.get_monotonic_time();
            this._resets = (this._resets ?? []).filter(t => now - t < 5e6);
            this._resets.push(now);
            if (this._resets.length > 3)
                throw new Error('o verificador do GDM não responde');
            if (this._ui.selected)
                this._begin();
        }));
        this._auth.begin(this._userName);
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
        if (this._grab)
            return true;
        const grab = Main.pushModal(Main.uiGroup, {actionMode: Shell.ActionMode.UNLOCK_SCREEN});
        if (grab.get_seat_state() !== Clutter.GrabState.ALL) {
            Main.popModal(grab);
            return false;
        }
        this._grab = grab;
        return true;
    }

    popModal() {
        if (this._grab)
            Main.popModal(this._grab);
        this._grab = null;
    }

    activate() {
        this.show();
        if (this._ui.selected && this._ui.entry.reactive)
            this._ui.entry.grab_key_focus();
        else
            super.grab_key_focus();     // (as setas escolhem a conta)
    }

    cancel() {
        this._deselect();
    }

    addCharacter(unichar) {
        // as in XP, typing only works after choosing the account
        if (!this._ui.selected)
            return;
        if (this._ui.entry.reactive && this._ui.entry.mapped)
            this._ui.entry.clutter_text.insert_unichar(unichar);
        else
            this._pending = (this._pending ?? '') + unichar;  // (texto: get_key_unicode)
    }

    finish(onComplete) {
        if (this._auth)
            this._auth.finish(onComplete);
        else
            onComplete();
    }

    _onDestroy() {
        this.popModal();
        this._userManager.disconnectObject(this);
        Main.layoutManager.disconnectObject(this);
        this._turnOffFlow?.destroy();
        this._auth?.destroy();
        this._auth = null;
        this._ui.destroy();
    }
});
