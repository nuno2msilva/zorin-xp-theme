/*
 * Os diálogos do XP "Desligar o computador" (msgina.dll, diálogo 20100) e
 * "Terminar sessão" (shell32.dll, diálogo 1089), com as imagens e os textos
 * desses binários. Partilhado: a extensão da sessão usa-o no menu Iniciar e o
 * build copia-o para a extensão do ecrã de boas-vindas (botão "Desligar
 * computador"). Os estilos (classes zxp-dialog e zxp-tooltip) vêm com ele.
 */
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';

import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {label} from './gdiText.js';

export const LOGOUT = 0, SHUTDOWN = 1, RESTART = 2;

// medidas dos modelos dos diálogos (DLU de Tahoma 8: x * 1,5 e y * 1,625 px)
export const DLG_W = 313, DLG_H = 198;    // fundo (msgina 20142); contorno de 1 px por fora
const TITLE = {x: 10, y: 0, w: 243, h: 42};
const FLAG = {x: 264, y: 1};
const ICON_Y = 80;
const LABEL_Y = 119;           // rótulos: 50x8 DLU por baixo dos ícones, centrados
const CANCEL = {x: 242, y: 167, w: 60, h: 20};
const TURN_OFF_BUTTONS = [   // Suspender, Desligar, Reiniciar
    {icon: 'standby', x: 54},
    {icon: 'turnoff', x: 140},
    {icon: 'restart', x: 225},
];
const LOG_OFF_BUTTONS = [    // Mudar de utilizador, Terminar sessão
    {icon: 'switchuser', x: 72},
    {icon: 'logoff', x: 210},
];
const TOOLTIP_DELAY = 500;


class XpTooltip {
    // dica em balão do XP: título a negrito e texto, fundo #FFFFE1
    constructor(parent, title, text) {
        const W = 260, PAD = 8, R = 6;
        this.actor = new St.Widget({layout_manager: new Clutter.FixedLayout(), reactive: false});
        const box = new St.BoxLayout({vertical: true, x: PAD, y: PAD, width: W - 2 * PAD});
        box.add_child(label('zxp-tooltip-title', title));
        const body = label('zxp-tooltip-text', text, {style: 'margin-top: 4px;', wrap: true});
        box.add_child(body);
        const [, bh] = box.get_preferred_height(W - 2 * PAD);
        const H = bh + 2 * PAD;
        const bg = new St.DrawingArea({width: W, height: H});
        bg.connect('repaint', area => {
            const cr = area.get_context();
            const l = 0.5, t = 0.5, r = W - 0.5, b = H - 0.5;
            cr.newSubPath();
            cr.arc(l + R, t + R, R, Math.PI, 1.5 * Math.PI);
            cr.arc(r - R, t + R, R, 1.5 * Math.PI, 0);
            cr.arc(r - R, b - R, R, 0, 0.5 * Math.PI);
            cr.arc(l + R, b - R, R, 0.5 * Math.PI, Math.PI);
            cr.closePath();
            cr.setSourceRGB(1, 1, 225 / 255);
            cr.fillPreserve();
            cr.setSourceRGB(0, 0, 0);
            cr.setLineWidth(1);
            cr.stroke();
            cr.$dispose();
        });
        this.actor.add_child(bg);
        this.actor.add_child(box);
        parent.add_child(this.actor);
    }

    destroy() {
        this.actor.destroy();
    }
}

export class XpDialog {
    // imgDir: pasta com as imagens (dialog-bg, ícones...); s: textos do XP
    constructor(imgDir, s, type, onAction) {
        this._img = imgDir;
        this._onAction = onAction;

        this.actor = new St.Widget({
            style_class: 'zxp-dialog',
            style: `background-image: url("${this._img}/dialog-bg.png");`,
            width: DLG_W + 2, height: DLG_H + 2,
            reactive: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        const title = label('zxp-dialog-title', type === LOGOUT ? s.logOffTitle : s.turnOffTitle, {
            x: TITLE.x, y: TITLE.y, width: TITLE.w, height: TITLE.h,
            yAlign: 'center', ellipsize: false,
        });
        this.actor.add_child(title);
        this.actor.add_child(new St.Widget({
            style: `background-image: url("${this._img}/dialog-flag.png");`,
            x: FLAG.x, y: FLAG.y, width: 48, height: 40,
        }));

        const canSuspend = SystemActions.getDefault().can_suspend;
        const buttons = type === LOGOUT
            ? [[LOG_OFF_BUTTONS[0], s.switchUser, s.tipSwitchUser, 'switch-user', true],
                [LOG_OFF_BUTTONS[1], s.logOffButton, s.tipLogOff, 'logout', true]]
            : [[TURN_OFF_BUTTONS[0], s.standby, s.tipStandby, 'suspend', canSuspend],
                [TURN_OFF_BUTTONS[1], s.turnOffButton, s.tipTurnOff, 'shutdown', true],
                [TURN_OFF_BUTTONS[2], s.restart, s.tipRestart, 'restart', true]];
        for (const [spec, text, tip, action, enabled] of buttons)
            this._iconButton(spec, text, tip, action, enabled);

        const cancel = new St.Button({
            style_class: 'zxp-dialog-cancel',
            child: label(null, s.cancel, {style: 'text-align: center;', yAlign: 'center',
                x_expand: true, y_expand: true, ellipsize: false}),
            x: CANCEL.x, y: CANCEL.y, width: CANCEL.w, height: CANCEL.h,
            can_focus: true,
        });
        cancel.connect('clicked', () => this._onAction('cancel'));
        this.actor.add_child(cancel);
        this._cancel = cancel;

        this.actor.connect('key-press-event', (_a, ev) => {
            if (ev.get_key_symbol() === Clutter.KEY_Escape) {
                this._onAction('cancel');
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
    }

    _iconButton(spec, text, tip, action, enabled) {
        const icon = new St.Widget({
            style: `background-image: url("${this._img}/${spec.icon}-${enabled ? 'normal' : 'disabled'}.png");`,
            width: 32, height: 32,
        });
        const button = new St.Button({
            child: icon, x: spec.x, y: ICON_Y, width: 32, height: 32,
            reactive: enabled, can_focus: enabled, track_hover: enabled,
        });
        const setState = st => {
            icon.style = `background-image: url("${this._img}/${spec.icon}-${st}.png");`;
        };
        // rótulo centrado por baixo do ícone (o St não centra uma linha só)
        const text_ = label(`zxp-dialog-label${enabled ? '' : ' disabled'}`, text, {y: LABEL_Y, ellipsize: false});
        text_.connect('notify::width', () => {
            text_.x = Math.round(spec.x + 16 - text_.width / 2);
        });
        if (enabled) {
            button.connect('notify::hover', () => {
                setState(button.hover ? 'hover' : 'normal');
                this._hideTooltip();
                if (button.hover) {
                    global.display.set_cursor(Meta.Cursor.POINTING_HAND);
                    this._tipTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, TOOLTIP_DELAY, () => {
                        this._tipTimer = 0;
                        this._showTooltip(button, text, tip);
                        return GLib.SOURCE_REMOVE;
                    });
                } else {
                    global.display.set_cursor(Meta.Cursor.DEFAULT);
                }
            });
            button.connect('notify::pressed', () => setState(button.pressed ? 'active' : button.hover ? 'hover' : 'normal'));
            button.connect('clicked', () => this._onAction(action));
        }
        this.actor.add_child(button);
        this.actor.add_child(text_);
    }

    _showTooltip(button, title, text) {
        if (!text)
            return;
        this._tooltip = new XpTooltip(global.stage, title, text);
        const [x, y] = button.get_transformed_position();
        this._tooltip.actor.set_position(Math.round(x + 16), Math.round(y + 40));
    }

    _hideTooltip() {
        if (this._tipTimer)
            GLib.source_remove(this._tipTimer);
        this._tipTimer = 0;
        this._tooltip?.destroy();
        this._tooltip = null;
    }

    destroy() {
        this._hideTooltip();
        global.display.set_cursor(Meta.Cursor.DEFAULT);
        this.actor.destroy();
    }
}
