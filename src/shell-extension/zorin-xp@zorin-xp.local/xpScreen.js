/*
 * XP's welcome screen (logonui.exe) inside the session: the "bem-vindo"
 * while the session loads and the status screens when logging off or
 * turning off ("A terminar a sessão...", "O Windows está a encerrar...").
 * The same measurements of UIFILE 1000 that the GDM extension uses; the
 * images and texts come from logonui.exe/winlogon.exe (logon/, made by the
 * build).
 */
import AccountsService from 'gi://AccountsService';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {label} from './gdiText.js';

import {isSessionStart} from './logonSound.js';

const TOP_H = 80;
const BOTTOM_H = 96;
const LINE_H = 2;
const PANEL_W = 384;
const LIST_X = 1 + 26;
const ITEM_W = PANEL_W - LIST_X - 5;
const ITEM_H = 80;
const FRAME = 58;
const PICTURE = 48;
const TEXT_X = 7 + FRAME + 7;

let _strings = null;

export function xpStrings(dir) {
    if (!_strings) {
        try {
            _strings = JSON.parse(new TextDecoder().decode(
                GLib.file_get_contents(`${dir}/logon/strings.json`)[1]));
        } catch (e) {
            logError(e, 'Zorin XP: textos do XP');
            _strings = {};
        }
    }
    return _strings;
}


export class XpScreen {
    constructor(dir) {
        this._img = `${dir}/logon/images`;
        this.strings = xpStrings(dir);
        // on top of everything (outside uiGroup, which GNOME animates on startup)
        // and catching the mouse: in XP nothing can be touched during these screens
        this.actor = new St.Widget({
            style_class: 'zxp-screen',
            reactive: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        const image = (name, w, h) => new St.Widget({
            style: `background-image: url("${this._img}/${name}.png");`,
            width: w, height: h,
        });
        this._top = new St.Widget({style_class: 'zxp-screen-top'});
        this._topLine = image('divider-top', 800, LINE_H);
        this._glow = image('glow', 219, 207);
        this._bottom = new St.Widget({style_class: 'zxp-screen-bottom'});
        // (bitmap 126 is 3 px high; XP stretches it to the line's 2 px)
        this._bottomLine = image('divider-bottom', 800, LINE_H);
        this._bottomLine.style += ' background-size: 800px 2px;';
        this._divider = image('divider-v', 1, 340);
        this._logo = image('logo', 137, 86);
        this._status = label('zxp-screen-status', '');
        this._welcomeShadow = label('zxp-screen-welcome-shadow', this.strings.welcome || '');
        this._welcome = label('zxp-screen-welcome', this.strings.welcome || '');
        this._tile = new St.Widget({layout_manager: new Clutter.FixedLayout(), width: ITEM_W, height: ITEM_H});
        this._frame = image('frame-hot', FRAME, FRAME);
        this._frame.set_position(7, 7);
        this._picture = new St.Widget({x: 12, y: 12, width: PICTURE, height: PICTURE});
        this._name = label('zxp-screen-name', '', {x: TEXT_X, y: 7, width: ITEM_W - TEXT_X - 14});
        this._tileStatus = label('zxp-screen-tile-status', '', {x: TEXT_X});
        for (const a of [this._frame, this._picture, this._name, this._tileStatus])
            this._tile.add_child(a);
        for (const a of [this._top, this._topLine, this._glow, this._bottom, this._bottomLine,
            this._divider, this._logo, this._status, this._welcomeShadow, this._welcome, this._tile])
            this.actor.add_child(a);
        this._mode = 'status';
        // the text measurements are only right after the font has been applied
        for (const l of [this._status, this._welcome, this._welcomeShadow, this._name])
            l.connect('style-changed', () => this._relayout());
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => this._relayout());
    }

    show() {
        global.stage.add_child(this.actor);
        global.stage.set_child_above_sibling(this.actor, null);
        this._relayout();
    }

    // "bem-vindo" on the left; the account on the right with the status below
    showWelcome(status) {
        this._mode = 'welcome';
        const um = AccountsService.UserManager.get_default();
        this._user = um.get_user(GLib.get_user_name());
        const sync = () => {
            const u = this._user;
            this._name.text = (u.is_loaded && u.get_real_name()) || GLib.get_real_name() || GLib.get_user_name();
            const icon = u.is_loaded ? u.get_icon_file() : null;
            const pic = icon && GLib.file_test(icon, GLib.FileTest.EXISTS) ? icon : `${this._img}/picture.png`;
            this._picture.style = `background-image: url("${pic}"); background-size: ${PICTURE}px ${PICTURE}px;`;
            this._relayout();
        };
        this._userId = this._user.connect('notify::is-loaded', sync);
        sync();
        this.setStatus(status);
        this.show();
    }

    // status alone: logo and text, the left panel centred on the screen
    showStatus(status) {
        this._mode = 'status';
        this.setStatus(status);
        this.show();
    }

    setStatus(text) {
        this._status.text = text || '';
        this._tileStatus.text = text || '';
        this._relayout();
    }

    _relayout() {
        const mon = Main.layoutManager.primaryMonitor;
        if (!mon)
            return;
        const {x, y, width: W, height: H} = mon;
        this.actor.set_position(x, y);
        this.actor.set_size(W, H);
        const top = TOP_H, bottom = H - BOTTOM_H, contentH = bottom - top;
        this._top.set_position(0, 0);
        this._top.set_size(W, TOP_H - LINE_H);
        this._topLine.set_position(0, TOP_H - LINE_H);
        this._topLine.scale_x = W / 800;
        this._glow.set_position(0, top);
        this._bottomLine.set_position(0, bottom);
        this._bottomLine.scale_x = W / 800;
        this._bottom.set_position(0, bottom + LINE_H);
        this._bottom.set_size(W, BOTTOM_H - LINE_H);

        const welcome = this._mode === 'welcome';
        this._divider.visible = this._tile.visible = welcome;
        this._welcome.visible = this._welcomeShadow.visible = welcome;
        this._logo.visible = this._status.visible = !welcome;

        if (welcome) {
            const div = Math.floor(W / 2) - 2;
            this._divider.set_position(div, top);
            this._divider.scale_y = contentH / 340;
            for (const [l, dx, dy] of [[this._welcomeShadow, 2, 3], [this._welcome, 0, 0]]) {
                const [, w] = l.get_preferred_width(-1);
                const [, h] = l.get_preferred_height(w);
                // (aligned by the last width: italic reaches past it, as in XP)
                l.set_position(div - 22 - l.textWidth + dx, top + Math.floor((contentH - h) / 2) + dy);
            }
            this._tile.set_position(div + LIST_X, top + Math.floor((contentH - ITEM_H) / 2));
            const [, nameH] = this._name.get_preferred_height(-1);
            this._tileStatus.y = 7 + nameH;
        } else {
            // without the right panel, the left one is centred (measured in XP)
            // (right-aligned by hand: St does not align a single line)
            const right = Math.floor(W / 2) + PANEL_W / 2;
            this._status.set_width(-1);
            const [, statusW] = this._status.get_preferred_width(-1);
            const w = Math.min(statusW, PANEL_W - 40);
            this._status.set_width(w);
            const [, statusH] = this._status.get_preferred_height(w);
            const by = top + Math.floor((contentH - (86 + 20 + statusH)) / 2);
            this._logo.set_position(right - 20 - 137, by);
            this._status.set_position(right - 40 - w, by + 86 + 20);
        }
    }

    destroy() {
        if (this._destroyed)
            return;
        this._destroyed = true;
        if (this._startupId)
            Main.layoutManager.disconnect(this._startupId);
        this._startupId = 0;
        if (this._monitorsId)
            Main.layoutManager.disconnect(this._monitorsId);
        this._monitorsId = 0;
        if (this._userId)
            this._user.disconnect(this._userId);
        this._userId = 0;
        this.actor.destroy();
    }
}

// welcome while the session loads (XP: "bem-vindo" and "A carregar as
// suas definições pessoais..."); it disappears at once when the desktop
// is ready
export function sessionWelcome(dir) {
    if (!isSessionStart())
        return null;
    const screen = new XpScreen(dir);
    screen.showWelcome(screen.strings.loadingSettings);
    // GNOME Shell would only show the screen after loading the background (the
    // black when logging on): with this, the session's first image is already
    // the XP screen
    global.stage.show();
    log('Zorin XP: [sessão] ecrã de boas-vindas mostrado');
    // the loading screen at the start of the session (zorin-xp-splash, launched
    // by ~/.xprofile) closes once this one has been drawn
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
        try {
            GLib.file_set_contents(
                GLib.build_filenamev([GLib.get_user_runtime_dir(), 'zorin-xp-splash.done']), '');
        } catch (e) {
            logError(e, 'Zorin XP: ecrã de carregamento');
        }
        return GLib.SOURCE_REMOVE;
    });
    const id = Main.layoutManager.connect('startup-complete', () => {
        Main.layoutManager.disconnect(id);
        screen._startupId = 0;
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 400, () => {
            screen.destroy();
            return GLib.SOURCE_REMOVE;
        });
    });
    screen._startupId = id;
    return screen;
}
