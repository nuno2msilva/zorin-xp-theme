// Zorin XP — o ecrã de boas-vindas do Windows XP substitui os ecrãs do GNOME:
//   - no GDM (modo gdm): o ecrã de início de sessão (loginDialog.js);
//   - na sessão (modos user/unlock-dialog): o ecrã bloqueado (unlockDialog.js).
//
// O GNOME Shell cria estes ecrãs com a classe que está em
// Main.sessionMode.unlockDialog; a extensão põe lá as do XP, e os diálogos do
// GNOME nunca chegam a ser criados. Se um diálogo do XP falhar (ao criar-se ou
// mais tarde), é trocado pelo do GNOME na hora: nunca se fica sem conseguir entrar.

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

        // XP: Win+L mostra logo o ecrã de boas-vindas (sem o deslizar do GNOME)
        const ss = Main.screenShield;
        if (ss && !Main.sessionMode.isGreeter) {
            const lock = ss.lock;
            ss.lock = function (_animate) {
                return lock.call(this, false);
            };
            // ...nem o escurecer logo a seguir a bloquear (o de inatividade fica)
            const fade = ss._activateFade;
            ss._activateFade = function (lightbox, time) {
                if (lightbox === this._shortLightbox)
                    return;
                fade.call(this, lightbox, time);
            };
        }
    }

    // põe a classe do XP em vez da do GNOME (a cada mudança de modo, porque o
    // GNOME volta a copiar os valores do modo para Main.sessionMode)
    _apply() {
        const key = Main.sessionMode.isGreeter ? 'gdm' : 'unlock';
        const current = Main.sessionMode.unlockDialog;
        if (current && current !== this._factory)
            this._originals.set(key, current);
        if (!this._gnome && this._originals.has(key))
            Main.sessionMode.unlockDialog = this._factory;
        this._syncPanel();
    }

    // a extensão arrancou depois de o GNOME já ter criado o diálogo dele
    // (normalmente não acontece: as extensões arrancam antes): trocar já
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

    // o painel de cima do GNOME (relógio, menus) não existe no ecrã de boas-vindas do XP
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

    // O GNOME Shell só começa a mostrar o ecrã depois de carregar o fundo do
    // sistema e de ficar desocupado (layout.js, _loadBackground): até lá a
    // placa mostra preto quando o Plymouth sai. O ecrã do XP fica já desenhado
    // por cima de tudo e o ecrã é mostrado logo; sai quando o diálogo
    // verdadeiro (igual) já está desenhado por baixo.
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

    // um diálogo do XP deu erro: trocar já pelo do GNOME
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
