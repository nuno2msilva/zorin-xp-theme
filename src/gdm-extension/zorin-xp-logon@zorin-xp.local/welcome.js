// Zorin XP — o ecrã de boas-vindas do Windows XP (logonui.exe): só a parte
// visual, usada pelo diálogo de início de sessão (GDM) e pelo de desbloqueio.
// Medidas do UIFILE 1000 do logonui.exe (px a 96 ppp) e de capturas do XP.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// (textos com as larguras de letra do XP: gdiText.js, copiado da extensão da sessão)
import {label} from './gdiText.js';

// o cursor de escrita pisca como no XP (GetCaretBlinkTime: 530 ms); o GNOME
// Shell não faz piscar o das suas caixas
const BLINK_MS = 530;
const TOP_H = 80;           // toppanel height=80rp (inclui a linha de 2)
const BOTTOM_H = 96;        // 2 + padding 20 + botão 26 + 2 + botão 26 + 20
const LINE_H = 2;
const PANEL_W = 384;        // leftpanel/rightpanel width=384rp
const LIST_X = 1 + 26;      // divisória 1rp + margem do scroller 26rp
const ITEM_W = PANEL_W - LIST_X - 5;
const ITEM_H = 80;
const PANE_H = 72;          // userpane: borda 5 + padding 2 + moldura 58 + 2 + 5
const FRAME = 58;
const PICTURE = 48;
const TEXT_X = 7 + FRAME + 7;
const PASS_X = 71;          // passwordpanelayer padding-left 71rp
const PASS_Y = 51;          // linha da palavra-passe dentro da conta (medido)
const EDIT_W = 163;
const EDIT_H = 28;
const OPTIONS_PAD = 25;     // options padding 25,20,25,20
const DIMMED = 96;          // hotaccountlistss: alpha 96 nas outras contas
const LIST_PAD = 26;        // selector padding rect(0,26,5,26): em cima e em baixo
const SCROLL_W = 17;        // barra do tema (SM_CXVSCROLL); setas 17x17 (SM_CYVSCROLL)
const SCROLL_STEP = 40;     // roda do rato / setas
const REPEAT_DELAY = 330;   // repetição das setas enquanto premidas (como no XP)
const REPEAT_RATE = 50;

export function loadStrings(dir) {
    try {
        return JSON.parse(new TextDecoder().decode(GLib.file_get_contents(`${dir}/strings.json`)[1]));
    } catch (e) {
        logError(e, 'Zorin XP: textos do XP');
        return {};
    }
}


function hand(actor) {
    actor.connect('enter-event', () => global.display.set_cursor(Meta.Cursor.POINTING_HAND));
    actor.connect('leave-event', () => global.display.set_cursor(Meta.Cursor.DEFAULT));
}

/*
 * Chamadas para fora (definidas por quem usa o ecrã):
 *   onUserClicked(nome), onSubmit(texto), onCancel(), onDeselect(), onTurnOff()
 * Contas: [{name, realName, iconFile, loggedIn}]
 */
export class XpWelcome {
    constructor(dir) {
        this._dir = dir;
        this.strings = loadStrings(dir);
        this._users = new Map();
        this._selected = null;
        this._hot = null;           // a conta realçada pelo teclado (como o rato)
        this._blinkId = 0;
        this._welcome = false;
        this.onUserClicked = this.onSubmit = this.onCancel = this.onDeselect = this.onTurnOff = () => {};
        this._build();
    }

    _image(name, props = {}) {
        return new St.Widget({
            style: `background-image: url("${this._dir}/images/${name}.png");`,
            ...props,
        });
    }

    _build() {
        const s = this.strings;
        this.actor = new St.Widget({
            style_class: 'zxp-logon',
            reactive: true,
            layout_manager: new Clutter.FixedLayout(),
        });
        // XP: clicar no fundo (fora das contas) tira a seleção e volta à lista
        this.actor.connect('button-press-event', (_a, ev) => {
            if (ev.get_button() !== 1 || this._welcome || !this._selected)
                return Clutter.EVENT_PROPAGATE;
            const target = global.stage.get_event_actor(ev);
            const inside = [...this._users.values()].map(u => u.actor)
                .concat([this._scrollbar, this._power, this._balloon])
                .some(a => a?.contains(target));
            if (inside)
                return Clutter.EVENT_PROPAGATE;
            this.onDeselect();
            return Clutter.EVENT_STOP;
        });

        this._top = new St.Widget({style_class: 'zxp-logon-top'});
        this._topLine = this._image('divider-top', {width: 800, height: LINE_H});
        this._glow = this._image('glow', {width: 219, height: 207});
        this._logo = this._image('logo', {width: 137, height: 86});
        this._help = label('zxp-logon-help', s.help, {wrap: true});
        this._status = label('zxp-logon-status-text', '');
        this._status.hide();
        this._welcomeShadow = label('zxp-logon-welcome-shadow', s.welcome, {opacity: 0});
        this._welcomeText = label('zxp-logon-welcome', s.welcome, {opacity: 0});
        this._divider = this._image('divider-v', {width: 1, height: 340});
        // lista de contas: recortada, com deslocamento quando não cabe
        this._list = new St.Widget({layout_manager: new Clutter.FixedLayout(),
            clip_to_allocation: true, reactive: true});
        this._list.connect('scroll-event', (_a, ev) => {
            // (cada passo da roda chega também como cópia "suave" emulada)
            if (ev.is_pointer_emulated())
                return Clutter.EVENT_STOP;
            const dir = ev.get_scroll_direction();
            if (dir === Clutter.ScrollDirection.UP)
                this._scrollBy(-SCROLL_STEP);
            else if (dir === Clutter.ScrollDirection.DOWN)
                this._scrollBy(SCROLL_STEP);
            else if (dir === Clutter.ScrollDirection.SMOOTH)
                this._scrollBy(ev.get_scroll_delta()[1] * SCROLL_STEP);
            return Clutter.EVENT_STOP;
        });
        this._scrollY = 0;
        this._buildScrollbar();

        this._bottom = new St.Widget({style_class: 'zxp-logon-bottom'});
        // (o bitmap 126 tem 3 px de altura; o XP estica-o para os 2 px da linha)
        this._bottomLine = this._image('divider-bottom', {width: 800, height: LINE_H});
        this._bottomLine.style += ' background-size: 800px 2px;';
        const powerBox = new St.BoxLayout({});
        powerBox.add_child(new St.Widget({style_class: 'zxp-logon-power-icon', y_align: Clutter.ActorAlign.CENTER}));
        powerBox.add_child(label('zxp-logon-power-label', s.turnOff, {
            y_align: Clutter.ActorAlign.CENTER, style: 'margin-left: 2px;',
        }));
        this._power = new St.Button({style_class: 'zxp-logon-power', child: powerBox, can_focus: true, track_hover: true});
        this._power.connect('clicked', () => this.onTurnOff());
        hand(this._power);
        this._instruct = label('zxp-logon-bottom-instruct', s.instructions, {wrap: true});

        for (const a of [this._top, this._topLine, this._glow, this._logo, this._help, this._status,
            this._welcomeShadow, this._welcomeText, this._divider, this._list, this._scrollbar,
            this._bottom, this._bottomLine, this._power, this._instruct])
            this.actor.add_child(a);
        for (const l of [this._help, this._status, this._welcomeShadow, this._welcomeText])
            l.connect('style-changed', () => this.relayout());

        // linha da palavra-passe (vai para dentro da conta selecionada)
        this._pass = new St.Widget({layout_manager: new Clutter.FixedLayout(), visible: false,
            width: ITEM_W, height: ITEM_H});
        this._passLabel = label('zxp-logon-instruct', s.password);
        this.entry = new St.PasswordEntry({
            style_class: 'zxp-logon-entry', can_focus: true,
            x: PASS_X, y: PASS_Y, width: EDIT_W, height: EDIT_H,
        });
        if ('show_peek_icon' in this.entry)
            this.entry.show_peek_icon = false;
        // bolinhas ao centro da área branca da caixa (medido)
        this.entry.clutter_text.translation_y = -1;
        this.entry.clutter_text.connect('activate', () => this._submit());
        this.entry.clutter_text.connect('text-changed', () => this.hideBalloon());
        this.entry.clutter_text.connect('key-press-event', (_a, ev) => {
            if (ev.get_key_symbol() === Clutter.KEY_Escape) {
                this.onCancel();
                return Clutter.EVENT_STOP;
            }
            this._restartBlink();
            return Clutter.EVENT_PROPAGATE;
        });
        // o cursor de escrita a piscar (sempre visível logo a seguir a escrever)
        this.entry.clutter_text.connect('key-focus-in', () => this._restartBlink());
        this.entry.clutter_text.connect('key-focus-out', () => this._stopBlink());
        this.entry.clutter_text.connect('text-changed', () => this._restartBlink());
        this._kbd = new St.Button({style_class: 'zxp-logon-kbd', can_focus: false});
        this._kbd.connect('clicked', () => this._nextInputSource());
        this._go = new St.Button({style_class: 'zxp-logon-go', can_focus: false, track_hover: true});
        this._go.connect('clicked', () => this._submit());
        hand(this._go);
        for (const a of [this._passLabel, this.entry, this._kbd, this._go])
            this._pass.add_child(a);

        this._sourceId = Main.inputSourceManager?.connect('current-source-changed', () => this._syncKeyboard());
        this._syncKeyboard();
    }

    _restartBlink() {
        this._stopBlink();
        const ct = this.entry.clutter_text;
        if (!ct.has_key_focus())
            return;
        ct.cursor_visible = true;
        this._blinkId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, BLINK_MS, () => {
            ct.cursor_visible = !ct.cursor_visible;
            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopBlink() {
        if (this._blinkId)
            GLib.source_remove(this._blinkId);
        this._blinkId = 0;
    }

    // ------------------------------------------------- teclado (lista de contas)
    // XP: com a lista à vista (nenhuma conta escolhida), as setas realçam as
    // contas como se o rato estivesse por cima (↓ começa pela primeira, ↑ pela
    // última), Enter escolhe a realçada e abre a palavra-passe; Esc tira o
    // realce. Devolve true se a tecla foi usada.
    handleListKey(ev) {
        if (this._welcome || this._selected || this._listHidden || !this.actor.visible)
            return false;
        const names = [...this._users.keys()];
        if (!names.length)
            return false;
        const sym = ev.get_key_symbol();
        const i = names.indexOf(this._hot);
        if (sym === Clutter.KEY_Down || sym === Clutter.KEY_KP_Down || sym === Clutter.KEY_Right) {
            this._setHot(names[i < 0 ? 0 : Math.min(i + 1, names.length - 1)]);
            return true;
        }
        if (sym === Clutter.KEY_Up || sym === Clutter.KEY_KP_Up || sym === Clutter.KEY_Left) {
            this._setHot(names[i < 0 ? names.length - 1 : Math.max(i - 1, 0)]);
            return true;
        }
        if ((sym === Clutter.KEY_Return || sym === Clutter.KEY_KP_Enter || sym === Clutter.KEY_space) && this._hot) {
            this.onUserClicked(this._hot);
            return true;
        }
        if (sym === Clutter.KEY_Escape && this._hot) {
            this._setHot(null);
            return true;
        }
        return false;
    }

    _setHot(name) {
        this._hot = name;
        if (name)
            this._ensureVisible(name);
        for (const u of this._users.values())
            this._updateUser(u);
    }

    _submit() {
        if (!this.entry.reactive)
            return;
        this.hideBalloon();
        this.onSubmit(this.entry.get_text());
    }

    // ------------------------------------------------------------ disposição
    relayout() {
        const mon = Main.layoutManager.primaryMonitor;
        if (!mon)
            return;
        const {width: W, height: H} = mon;
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
        const optY = bottom + LINE_H + 20;
        this._power.set_position(OPTIONS_PAD, optY);
        this._instruct.set_width(325 - 18);
        this._instruct.set_position(W - OPTIONS_PAD - 325 + 18, optY);

        const statusMode = this._status.visible;
        this._divider.visible = !statusMode;
        this._list.visible = !statusMode && !this._listHidden;
        if (statusMode || this._listHidden)
            this._scrollbar.hide();
        this._help.visible = !statusMode && !this._welcome && !this._listHidden;
        // (nos ecrãs de estado do XP a barra de baixo fica vazia)
        this._power.visible = this._instruct.visible = !statusMode && !this._welcome;
        // no ecrã de estado (sem contas) o painel esquerdo fica centrado
        const div = statusMode ? Math.floor(W / 2) + PANEL_W / 2 : Math.floor(W / 2) - 2;
        this._divider.set_position(div, top);
        this._divider.scale_y = contentH / 340;

        let textH;
        let text = this._help;
        if (statusMode) {
            // (alinhado à direita à mão: o St não alinha uma linha só)
            text = this._status;
            text.set_width(-1);
            const [, w] = text.get_preferred_width(-1);
            text.set_width(Math.min(w, PANEL_W - 40));
            [, textH] = text.get_preferred_height(text.width);
        } else if (this._listHidden) {
            textH = 0;
        } else {
            text.set_width(PANEL_W - 40);
            [, textH] = text.get_preferred_height(PANEL_W - 40);
        }
        const blockH = 86 + 20 + textH;
        const by = top + Math.floor((contentH - blockH) / 2);
        this._logo.set_position(div - 20 - 137, by);
        text.set_position(div - 40 - text.width, by + 86 + 20);

        for (const [l, dx, dy] of [[this._welcomeShadow, 2, 3], [this._welcomeText, 0, 0]]) {
            const [, w] = l.get_preferred_width(-1);
            const [, h] = l.get_preferred_height(w);
            // (alinhado pela última largura: o itálico passa para lá dela, como no XP)
            l.set_position(div - 22 - l.textWidth + dx, top + Math.floor((contentH - h) / 2) + dy);
        }

        this._list.set_position(div + LIST_X, top);
        this._list.set_size(PANEL_W - LIST_X, contentH);
        this._scrollbar.set_position(div + PANEL_W - SCROLL_W, top);
        this._contentH = contentH;
        this._layoutUsers();
    }

    // ------------------------------------------------------------- contas
    setUsers(list) {
        const names = list.map(u => u.name);
        for (const [name, u] of this._users) {
            if (!names.includes(name)) {
                if (this._pass.get_parent() === u.actor)
                    u.actor.remove_child(this._pass);
                u.actor.destroy();
                this._users.delete(name);
            }
        }
        for (const info of list) {
            let u = this._users.get(info.name);
            if (!u) {
                u = this._makeUser(info.name);
                this._users.set(info.name, u);
                this._list.add_child(u.actor);
            }
            u.info = info;
            this._updateUser(u);
        }
        this._layoutUsers();
    }

    _makeUser(name) {
        const u = {name};
        u.actor = new St.Widget({
            reactive: true, track_hover: true,
            layout_manager: new Clutter.FixedLayout(),
            width: ITEM_W, height: ITEM_H,
        });
        u.select = this._image('select', {width: ITEM_W, height: PANE_H, visible: false});
        u.frame = new St.Widget({x: 7, y: 7, width: FRAME, height: FRAME});
        u.picture = new St.Widget({x: 7 + (FRAME - PICTURE) / 2, y: 7 + (FRAME - PICTURE) / 2,
            width: PICTURE, height: PICTURE});
        u.nameLabel = label('zxp-logon-name', '', {x: TEXT_X, y: 7, width: ITEM_W - TEXT_X - 14});
        u.status = label('zxp-logon-status', '', {x: TEXT_X});
        // (a imagem é filha da moldura no XP: fica por cima)
        for (const a of [u.select, u.frame, u.picture, u.nameLabel, u.status])
            u.actor.add_child(a);
        // XP: com o rato numa conta, as outras esbatem-se; fora da lista, nenhuma
        u.actor.connect('notify::hover', () => {
            for (const v of this._users.values())
                this._updateUser(v);
        });
        u.actor.connect('enter-event', () => {
            if (this._hot) {
                this._hot = null;
                for (const v of this._users.values())
                    this._updateUser(v);
            }
            if (!(this._selected === name && this._pass.visible))
                global.display.set_cursor(Meta.Cursor.POINTING_HAND);
        });
        u.actor.connect('leave-event', () => global.display.set_cursor(Meta.Cursor.DEFAULT));
        u.actor.connect('button-release-event', (_a, ev) => {
            if (ev.get_button() === 1 && !this._welcome)
                this.onUserClicked(name);
            return Clutter.EVENT_STOP;
        });
        return u;
    }

    _updateUser(u) {
        const info = u.info;
        if (!info)
            return;
        const selected = this._selected === u.name;
        u.nameLabel.text = info.realName || u.name;
        const pic = info.iconFile && GLib.file_test(info.iconFile, GLib.FileTest.EXISTS)
            ? info.iconFile : `${this._dir}/images/picture.png`;
        u.picture.style = `background-image: url("${pic}"); background-size: ${PICTURE}px ${PICTURE}px;`;
        const hot = u.actor.hover || this._hot === u.name;
        u.frame.style = `background-image: url("${this._dir}/images/${
            selected || hot ? 'frame-hot' : 'frame'}.png");`;
        u.select.visible = selected && !this._welcome;
        u.status.style_class = selected ? 'zxp-logon-status selected' : 'zxp-logon-status';
        let status = '';
        if (selected && this._statusText)
            status = this._statusText;
        else if (info.loggedIn)
            status = this.strings.loggedOn;
        u.status.text = status;
        u.status.visible = !!status && !(selected && this._pass.visible);
        const [, nameH] = u.nameLabel.get_preferred_height(-1);
        u.status.y = 7 + nameH;
        const hovering = [...this._users.values()].some(v => v.actor.hover || this._hot === v.name);
        u.actor.opacity = hovering && !selected && !hot ? DIMMED : 255;
    }

    _layoutUsers() {
        if (this._welcome || !this._contentH)
            return;
        const list = [...this._users.values()];
        const total = LIST_PAD * 2 + list.length * ITEM_H;
        // XP: se couberem, centradas na vertical; senão, a partir de cima com a
        // barra de deslocamento do tema encostada ao fim do painel
        this._overflow = total > this._contentH;
        this._maxScroll = Math.max(0, total - this._contentH);
        this._scrollY = Math.min(Math.max(0, this._scrollY), this._maxScroll);
        const width = this._overflow ? PANEL_W - LIST_X - SCROLL_W - 5 : ITEM_W;
        let y = this._overflow ? LIST_PAD - this._scrollY
            : Math.max(LIST_PAD, Math.floor((this._contentH - list.length * ITEM_H) / 2));
        for (const u of list) {
            this._setItemWidth(u, width);
            u.actor.set_position(0, y);
            y += ITEM_H;
        }
        this._layoutScrollbar();
    }

    _setItemWidth(u, w) {
        if (u.width === w)
            return;
        u.width = w;
        u.actor.width = w;
        u.select.width = w;
        u.select.style = `background-image: url("${this._dir}/images/select.png"); background-size: ${w}px ${PANE_H}px;`;
        u.nameLabel.width = w - TEXT_X - 14;
    }

    // ---------------------------------------------------- barra de deslocamento
    _scrollImage(name) {
        return `background-image: url("${this._dir}/images/scroll-${name}.png");`;
    }

    _buildScrollbar() {
        this._scrollbar = new St.Widget({layout_manager: new Clutter.FixedLayout(), visible: false,
            reactive: true, width: SCROLL_W});
        this._track = new St.Widget({reactive: true, width: SCROLL_W});
        this._track.connect('button-press-event', (_a, ev) => {
            const [, ey] = ev.get_coords();
            const [, ty] = this._thumb.get_transformed_position();
            const page = this._contentH - ITEM_H;
            this._startRepeat(() => this._scrollBy(ey < ty ? -page : page));
            return Clutter.EVENT_STOP;
        });
        this._track.connect('button-release-event', () => this._stopRepeat());
        this._up = this._arrow('up', -SCROLL_STEP);
        this._down = this._arrow('down', SCROLL_STEP);
        // cursor: topo, meio esticado e base (as margens do Luna são 5 px) + riscas
        this._thumb = new St.Widget({layout_manager: new Clutter.FixedLayout(), reactive: true,
            track_hover: true, width: SCROLL_W});
        this._thumbTop = new St.Widget({width: SCROLL_W, height: 5});
        this._thumbMid = new St.Widget({width: SCROLL_W, y: 5});
        this._thumbBottom = new St.Widget({width: SCROLL_W, height: 5});
        this._grip = new St.Widget({width: SCROLL_W});
        for (const a of [this._thumbTop, this._thumbMid, this._thumbBottom, this._grip])
            this._thumb.add_child(a);
        this._thumb.connect('notify::hover', () => this._paintThumb());
        this._thumb.connect('button-press-event', (_a, ev) => {
            this._drag = {y: ev.get_coords()[1], scroll: this._scrollY};
            this._paintThumb();
            this._dragId = global.stage.connect('captured-event', (_s, e) => {
                const t = e.type();
                if (t === Clutter.EventType.MOTION) {
                    const range = this._trackLen - this._thumbLen;
                    if (range > 0)
                        this._scrollTo(this._drag.scroll + (e.get_coords()[1] - this._drag.y) * this._maxScroll / range);
                    return Clutter.EVENT_STOP;
                }
                if (t === Clutter.EventType.BUTTON_RELEASE) {
                    global.stage.disconnect(this._dragId);
                    this._dragId = 0;
                    this._drag = null;
                    this._paintThumb();
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            });
            return Clutter.EVENT_STOP;
        });
        for (const a of [this._track, this._up, this._down, this._thumb])
            this._scrollbar.add_child(a);
        this._paintThumb();
    }

    _arrow(dir, step) {
        const b = new St.Widget({reactive: true, track_hover: true, width: SCROLL_W, height: SCROLL_W,
            style: this._scrollImage(`${dir}-normal`)});
        const paint = pressed => {
            b.style = this._scrollImage(`${dir}-${pressed ? 'active' : b.hover ? 'hover' : 'normal'}`);
        };
        b.connect('notify::hover', () => paint(false));
        b.connect('button-press-event', () => {
            paint(true);
            this._startRepeat(() => this._scrollBy(step));
            return Clutter.EVENT_STOP;
        });
        b.connect('button-release-event', () => {
            paint(false);
            this._stopRepeat();
            return Clutter.EVENT_STOP;
        });
        b.connect('leave-event', () => this._stopRepeat());
        return b;
    }

    _paintThumb() {
        const st = this._drag ? 'active' : this._thumb.hover ? 'hover' : 'normal';
        this._thumbTop.style = this._scrollImage(`thumb-top-${st}`);
        this._thumbBottom.style = this._scrollImage(`thumb-bottom-${st}`);
        this._thumbMid.style = `${this._scrollImage(`thumb-mid-${st}`)} background-size: ${SCROLL_W}px ${
            Math.max(1, this._thumbLen - 10)}px;`;
        this._grip.style = this._scrollImage(`grip-${st}`);
    }

    _layoutScrollbar() {
        this._scrollbar.visible = this._overflow && !this._status.visible && !this._listHidden;
        if (!this._overflow)
            return;
        const H = this._contentH;
        this._scrollbar.height = H;
        this._trackLen = H - 2 * SCROLL_W;
        this._up.set_position(0, 0);
        this._down.set_position(0, H - SCROLL_W);
        this._track.set_position(0, SCROLL_W);
        this._track.height = this._trackLen;
        this._track.style = `${this._scrollImage('track')} background-size: ${SCROLL_W}px ${this._trackLen}px;`;
        const total = this._maxScroll + H;
        this._thumbLen = Math.max(SCROLL_W, Math.round(this._trackLen * H / total));
        const pos = this._maxScroll ? Math.round((this._trackLen - this._thumbLen) * this._scrollY / this._maxScroll) : 0;
        this._thumb.set_position(0, SCROLL_W + pos);
        this._thumb.height = this._thumbLen;
        this._thumbMid.height = this._thumbLen - 10;
        this._thumbBottom.y = this._thumbLen - 5;
        this._grip.height = this._thumbLen;   // riscas centradas (tamanho real)
        this._paintThumb();
    }

    _scrollTo(y) {
        if (!this._overflow)
            return;
        const v = Math.min(Math.max(0, Math.round(y)), this._maxScroll);
        if (v === this._scrollY)
            return;
        this._scrollY = v;
        this.hideBalloon();
        this._layoutUsers();
    }

    _scrollBy(dy) {
        this._scrollTo(this._scrollY + dy);
    }

    _startRepeat(fn) {
        this._stopRepeat();
        fn();
        this._repeatId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, REPEAT_DELAY, () => {
            this._repeatId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, REPEAT_RATE, () => {
                fn();
                return GLib.SOURCE_CONTINUE;
            });
            return GLib.SOURCE_REMOVE;
        });
    }

    _stopRepeat() {
        if (this._repeatId)
            GLib.source_remove(this._repeatId);
        this._repeatId = 0;
    }

    // a conta escolhida fica toda à vista
    _ensureVisible(name) {
        const list = [...this._users.keys()];
        const i = list.indexOf(name);
        if (!this._overflow || i < 0)
            return;
        const top = LIST_PAD + i * ITEM_H;
        if (top < this._scrollY)
            this._scrollTo(top - LIST_PAD);
        else if (top + ITEM_H > this._scrollY + this._contentH)
            this._scrollTo(top + ITEM_H - this._contentH + LIST_PAD);
    }

    get selected() {
        return this._selected;
    }

    get userCount() {
        return this._users.size;
    }

    select(name) {
        this._selected = name;
        this._hot = null;           // (Esc volta à lista sem realce, como no XP)
        this._statusText = null;
        this.hideBalloon();
        if (!name)
            this.hidePrompt();
        else
            this._ensureVisible(name);
        for (const u of this._users.values())
            this._updateUser(u);
    }

    // ------------------------------------------------------ palavra-passe
    showPrompt(question, secret) {
        const u = this._users.get(this._selected);
        if (!u)
            return;
        this._passLabel.text = secret ? this.strings.password : question || '';
        this.entry.password_visible = !secret;
        this.entry.set_text('');
        this.entry.reactive = true;
        if (this._pass.get_parent() !== u.actor) {
            this._pass.get_parent()?.remove_child(this._pass);
            u.actor.add_child(this._pass);
        }
        const [, h] = this._passLabel.get_preferred_height(-1);
        this._passLabel.set_position(PASS_X + 3, PASS_Y - 3 - h);
        const [, kw] = this._kbd.get_preferred_width(-1);
        const [, kh] = this._kbd.get_preferred_height(-1);
        this._kbd.set_position(PASS_X + EDIT_W + 5, PASS_Y + Math.floor((EDIT_H - kh) / 2));
        this._go.set_position(PASS_X + EDIT_W + 5 + (this._kbd.visible ? kw + 5 : 0), PASS_Y + 1);
        this._pass.show();
        this.entry.grab_key_focus();
        for (const v of this._users.values())
            this._updateUser(v);
    }

    hidePrompt() {
        this._pass.hide();
        for (const v of this._users.values())
            this._updateUser(v);
    }

    setBusy(busy) {
        this.entry.reactive = !busy;
    }

    // "A iniciar sessão...", etc., por baixo do nome da conta selecionada
    setUserStatus(text) {
        this._statusText = text;
        this.hidePrompt();
    }

    // XP: depois de entrar, o logótipo dá lugar a "bem-vindo" e as outras contas somem
    showWelcome(text) {
        this._welcome = true;
        this._statusText = text;
        this.hideBalloon();
        this._pass.hide();
        this._logo.opacity = 0;
        this._help.hide();
        this._welcomeShadow.opacity = this._welcomeText.opacity = 255;
        this._power.hide();
        this._instruct.hide();
        for (const u of this._users.values()) {
            if (u.name !== this._selected)
                u.actor.hide();
            this._updateUser(u);
        }
    }

    // XP: enquanto pergunta se desliga com outras sessões abertas, as contas e
    // a ajuda desaparecem (fica o logótipo e a barra de baixo)
    setListHidden(hidden) {
        this._listHidden = hidden;
        this.relayout();
    }

    // ecrã de estado sem contas ("O Windows está a iniciar...")
    showStatus(text) {
        this._status.text = text || '';
        this._status.visible = !!text;
        this.relayout();
    }

    // -------------------------------------------- balão de palavra errada
    showBalloon(title, text) {
        this.hideBalloon();
        const u = this._users.get(this._selected);
        if (!u)
            return;
        const W = 300, PAD = 10, STEM = 18, R = 8;
        const box = new St.BoxLayout({vertical: true, x: PAD, y: STEM + PAD, width: W - 2 * PAD});
        box.add_child(label('zxp-logon-balloon-title', title ?? this.strings.forgot));
        box.add_child(label('zxp-logon-balloon-text', text ?? this.strings.badPassword,
            {wrap: true, style: 'margin-top: 6px;'}));
        const [, bh] = box.get_preferred_height(W - 2 * PAD);
        const H = STEM + bh + 2 * PAD;
        const bubble = new St.DrawingArea({width: W, height: H, reactive: true});
        bubble.connect('repaint', area => {
            const cr = area.get_context();
            const t = STEM + 0.5, b = H - 0.5, l = 0.5, r = W - 0.5;
            cr.newSubPath();
            cr.arc(l + R, t + R, R, Math.PI, 1.5 * Math.PI);
            cr.lineTo(l + 20, t);
            cr.lineTo(l + 20, 0.5);           // ponta do balão, a apontar para a caixa
            cr.lineTo(l + 20 + STEM, t);
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
        bubble.connect('button-press-event', () => {
            this.hideBalloon();
            return Clutter.EVENT_STOP;
        });
        const balloon = new St.Widget({layout_manager: new Clutter.FixedLayout()});
        balloon.add_child(bubble);
        balloon.add_child(box);
        const [ax, ay] = this.actor.get_transformed_position();
        const [ux, uy] = u.actor.get_transformed_position();
        balloon.set_position(ux - ax + PASS_X + 10, uy - ay + PASS_Y + EDIT_H - 4);
        this.actor.add_child(balloon);
        this._balloon = balloon;
    }

    hideBalloon() {
        this._balloon?.destroy();
        this._balloon = null;
    }

    // ------------------------------------------------------------ teclado
    _syncKeyboard() {
        const src = Main.inputSourceManager?.currentSource;
        this._kbd.label = src ? (src.shortName || '').toUpperCase() : '';
        this._kbd.visible = !!this._kbd.label;
    }

    _nextInputSource() {
        const mgr = Main.inputSourceManager;
        if (!mgr)
            return;
        const sources = Object.values(mgr.inputSources).sort((a, b) => a.index - b.index);
        if (sources.length < 2)
            return;
        sources[(sources.indexOf(mgr.currentSource) + 1) % sources.length].activate(true);
    }

    destroy() {
        this._stopBlink();
        this._stopRepeat();
        if (this._dragId)
            global.stage.disconnect(this._dragId);
        this._dragId = 0;
        if (this._sourceId)
            Main.inputSourceManager?.disconnect(this._sourceId);
        this._sourceId = 0;
        this.hideBalloon();
        this._pass.destroy();
        this.actor.destroy();
        global.display.set_cursor(Meta.Cursor.DEFAULT);
    }
}
