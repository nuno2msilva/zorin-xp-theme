// Zorin XP — ecrã bloqueado (Win+L, mudar de utilizador) é o ecrã de boas-vindas
// do XP, como no XP com a mudança rápida de utilizador.
//
// Substitui o UnlockDialog do GNOME (Main.sessionMode.unlockDialog): como no
// XP, abre com a lista de contas sem nenhuma selecionada; clicar na conta com
// a sessão bloqueada mostra a caixa da palavra-passe (Esc ou um clique no fundo
// voltam à lista) e clicar noutra conta passa para o ecrã de início de sessão (GDM). A verificação é a
// reautenticação do GDM (auth.js); quando aceita, o GDM desbloqueia a sessão
// (sinal Unlock do logind) e o ScreenShield fecha este diálogo.

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
                loggedIn: () => true,        // a própria sessão está iniciada
                power: action => {
                    // pelo gnome-session (as aplicações fecham como deve ser),
                    // através da extensão da sessão; senão, pelo logind
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

        // qualquer tecla ou movimento acorda o ecrã (se tiver escurecido)
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
        // a própria conta aparece sempre, mesmo antes de o AccountsService carregar
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
            // outra conta: o ecrã de início de sessão do GDM (mudar de utilizador)
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
        // (as setas voltam a andar pela lista)
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
            // recomeçar; se o GDM não responder e isto entrar em ciclo, fica o GNOME
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

    // -------------------------------------------- o que o ScreenShield usa
    // (o ScreenShield dá o foco ao diálogo: vai para a caixa da palavra-passe)
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
        // como no XP, só se escreve depois de escolher a conta
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
