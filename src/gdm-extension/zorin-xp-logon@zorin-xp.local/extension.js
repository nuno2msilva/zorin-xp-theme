// Zorin XP — the Windows XP welcome screen replaces GNOME's screens:
//   - in GDM (gdm mode): the login screen (loginDialog.js);
//   - in the session (user/unlock-dialog modes): the lock screen (unlockDialog.js).
//
// GNOME Shell creates these screens with the class in
// Main.sessionMode.unlockDialog; the extension puts XP's there, and GNOME's
// dialogs are never created. If an XP dialog fails (when created or later),
// it is swapped for GNOME's on the spot: you are never left unable to log in.

import GLib from 'gi://GLib';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {XpLoginDialog, uptime} from './loginDialog.js';
import {XpUnlockDialog} from './unlockDialog.js';
import {XpWelcome} from './welcome.js';

export default class ZorinXpWelcomeExtension extends Extension {
    enable() {
        if (GLib.getenv('ZXP_LOGON_TEST'))
            global.context.unsafe_mode = true;  // testes: Eval por D-Bus
        this._gnome = false;
        this._originals = new Map();          // classe original do GNOME por modo
        const ext = this;
        this._factory = function (parentActor) {
            const greeter = Main.sessionMode.isGreeter;
            const Orig = ext._originals.get(greeter ? 'gdm' : 'unlock');
            try {
                return greeter ? new XpLoginDialog(parentActor, ext) : new XpUnlockDialog(parentActor, ext);
            } catch (e) {
                logError(e, 'Zorin XP: ecrã de boas-vindas — fica o do GNOME');
                ext._useGnome();
                return new Orig(parentActor);
            }
        };
        this._apply();
        this._modeId = Main.sessionMode.connect('updated', () => this._apply());
        this._replaceExisting();
        if (Main.sessionMode.isGreeter && Main.layoutManager._startingUp)
            this._showCover();

        // XP: Win+L shows the welcome screen at once (without GNOME's slide)
        const ss = Main.screenShield;
        if (ss && !Main.sessionMode.isGreeter) {
            const lock = ss.lock;
            ss.lock = function (_animate) {
                return lock.call(this, false);
            };
            // ...nor the dimming right after locking (the idle one stays)
            const fade = ss._activateFade;
            ss._activateFade = function (lightbox, time) {
                if (lightbox === this._shortLightbox)
                    return;
                fade.call(this, lightbox, time);
            };
        }
    }

    // puts XP's class instead of GNOME's (on every mode change, because GNOME
    // copies the mode's values to Main.sessionMode again)
    _apply() {
        const key = Main.sessionMode.isGreeter ? 'gdm' : 'unlock';
        const current = Main.sessionMode.unlockDialog;
        if (current && current !== this._factory)
            this._originals.set(key, current);
        if (!this._gnome && this._originals.has(key))
            Main.sessionMode.unlockDialog = this._factory;
        this._syncPanel();
    }

    // the extension started after GNOME had already created its dialog
    // (normally it does not happen: extensions start before): swap it now
    _replaceExisting() {
        const ss = Main.screenShield;
        const d = ss?._dialog;
        if (!d || d instanceof XpLoginDialog || d instanceof XpUnlockDialog)
            return;
        if (!Main.sessionMode.isGreeter && !Main.sessionMode.isLocked)
            return;
        try {
            d.popModal?.();
            d.close?.();
            ss._dialog = null;
            d.destroy();
            ss._ensureUnlockDialog(true);
        } catch (e) {
            logError(e, 'Zorin XP: trocar o diálogo do GNOME');
        }
    }

    // GNOME's top panel (clock, menus) does not exist on XP's welcome screen
    _syncPanel() {
        const box = Main.layoutManager.panelBox;
        const xp = !this._gnome && (Main.sessionMode.isGreeter || Main.sessionMode.isLocked);
        if (xp && !this._panelHidden) {
            this._panelHidden = true;
            box.hide();
            this._panelId = box.connect('notify::visible', () => {
                if (this._panelHidden && box.visible)
                    box.hide();
            });
        } else if (!xp && this._panelHidden) {
            this._showPanel();
        }
    }

    _showPanel() {
        this._panelHidden = false;
        if (this._panelId)
            Main.layoutManager.panelBox.disconnect(this._panelId);
        this._panelId = 0;
        Main.layoutManager.panelBox.show();
    }

    // GNOME Shell only starts showing the screen after loading the system
    // background and becoming idle (layout.js, _loadBackground): until then the
    // card shows black when Plymouth leaves. The XP screen is drawn right away
    // on top of everything and the screen is shown at once; it leaves when the
    // real dialog (identical) has been drawn underneath.
    _showCover() {
        try {
            const cover = new XpWelcome(this.path);
            if (uptime() < 180)
                cover.showStatus(cover.strings.starting);
            global.stage.add_child(cover.actor);
            const sync = () => {
                const m = Main.layoutManager.primaryMonitor;
                if (m) {
                    cover.actor.set_position(m.x, m.y);
                    cover.relayout();
                    log(`Zorin XP: [arranque] capa ${m.width}x${m.height}`);
                }
            };
            sync();
            this._coverMonId = Main.layoutManager.connect('monitors-changed', sync);
            this._cover = cover;
            global.stage.show();
            this._coverTimeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 20, () => {
                this._coverTimeout = 0;
                this.coverDone();
                return GLib.SOURCE_REMOVE;
            });
            log('Zorin XP: [arranque] capa mostrada');
        } catch (e) {
            logError(e, 'Zorin XP: ecrã de arranque');
            this.coverDone();
        }
    }

    coverDone() {
        if (this._coverTimeout)
            GLib.source_remove(this._coverTimeout);
        this._coverTimeout = 0;
        if (this._coverMonId)
            Main.layoutManager.disconnect(this._coverMonId);
        this._coverMonId = 0;
        if (this._cover) {
            this._cover.destroy();
            this._cover = null;
            log('Zorin XP: [arranque] capa retirada');
        }
    }

    _useGnome() {
        this.coverDone();
        this._gnome = true;
        for (const [key, Orig] of this._originals) {
            if ((key === 'gdm') === Main.sessionMode.isGreeter)
                Main.sessionMode.unlockDialog = Orig;
        }
        this._showPanel();
    }

    // an XP dialog failed: swap it for GNOME's now

    fallback(dialog, error) {
        logError(error, 'Zorin XP: ecrã de boas-vindas — a voltar ao do GNOME');
        if (this._gnome)
            return;
        this._useGnome();
        const ss = Main.screenShield;
        try {
            dialog.popModal?.();
            dialog.close?.();
        } catch (e) {}
        if (ss && ss._dialog === dialog) {
            ss._dialog = null;
            dialog.destroy();
            try {
                ss._ensureUnlockDialog(true);
            } catch (e) {
                logError(e, 'Zorin XP: diálogo do GNOME');
            }
        } else {
            dialog.destroy();
        }
    }

    disable() {
        this.coverDone();
        if (this._modeId)
            Main.sessionMode.disconnect(this._modeId);
        this._modeId = 0;
        if (Main.sessionMode.unlockDialog === this._factory) {
            const key = Main.sessionMode.isGreeter ? 'gdm' : 'unlock';
            Main.sessionMode.unlockDialog = this._originals.get(key) ?? null;
        }
        for (const m of ['lock', '_activateFade']) {
            if (Main.screenShield && Object.hasOwn(Main.screenShield, m))
                delete Main.screenShield[m];
        }
        if (this._panelHidden)
            this._showPanel();
        this._factory = null;
    }
}
