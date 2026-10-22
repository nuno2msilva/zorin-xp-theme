/*
 * Zorin XP — Molduras
 *
 * Nas janelas X11 com moldura do servidor (mutter-x11-frames), o mutter 46
 * só aceita moldura em cima (as extensões direita/inferior estão fixas a 0),
 * e o GTK4 não deixa alinhar o título à esquerda. O tema GTK desenha a
 * legenda sem as 4 colunas de moldura de cada lado; esta extensão
 * acrescenta, como filho do ator da janela (acompanha movimento, animações
 * e miniaturas da vista geral, sem intercetar o rato):
 *   - as 4 colunas de cada lado da legenda (cantos arredondados),
 *   - as bordas esquerda, direita e inferior de 4 px,
 *   - o ícone 16×16 em (6, 8) e o título a partir de x = 26.
 * Medidas confirmadas ao píxel contra capturas reais do Windows XP.
 */
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Pango from 'gi://Pango';
import Shell from 'gi://Shell';
import St from 'gi://St';


const BORDER = 4;          // SM_CXSIZEFRAME
const CAPTION = 30;        // SM_CYCAPTION (26) + moldura (4)
const ICON_X = 6, ICON_Y = 8, ICON_SIZE = 16;
const TEXT_X = 26;
const BUTTONS_WIDTH = 73;  // do botão minimizar até à direita
// peças dos lados da legenda: 4 colunas de moldura + 8 do canto arredondado
// (que o GTK corta na janela das molduras do mutter; só as 6 linhas de cima)
const CAPTION_SIDE = 12;

export class XpFrame {
    constructor(ext, metaWindow, actor) {
        this._ext = ext;
        this._win = metaWindow;
        this._actor = actor;

        this._box = new St.Widget({reactive: false, x_expand: false, y_expand: false});
        this._parts = {};
        for (const name of ['capLeft', 'capRight', 'left', 'right', 'bottom'])
            this._box.add_child(this._parts[name] = new St.Widget({reactive: false}));

        this._icon = new St.Bin({reactive: false, width: ICON_SIZE, height: ICON_SIZE});
        this._title = new St.Label({reactive: false, style_class: 'zxp-title'});
        this._title.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        this._box.add_child(this._icon);
        this._box.add_child(this._title);
        actor.add_child(this._box);

        const w = this._win;
        this._signals = [
            w.connect('size-changed', () => this._queue()),
            w.connect('position-changed', () => this._queue()),
            w.connect('notify::title', () => this._updateTitle()),
            w.connect('notify::appears-focused', () => this._update()),
            w.connect('notify::maximized-horizontally', () => this._queue()),
            w.connect('notify::maximized-vertically', () => this._queue()),
            w.connect('notify::fullscreen', () => this._queue()),
            w.connect('notify::wm-class', () => this._updateIcon()),
        ];
        this._actorDestroy = actor.connect('destroy', () => this.destroy(false));
        this._updateIcon();
        this._updateTitle();
        this._update();
    }

    _queue() {
        if (this._idle)
            return;
        this._idle = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._idle = 0;
            this._update();
            return GLib.SOURCE_REMOVE;
        });
    }

    _asset(name) {
        return `url("file://${this._ext.path}/assets/${name}.png")`;
    }

    _updateIcon() {
        // (um ícone escolhido para a janela — o favicon da página no IE, ver
        // zenIcons.js — ou o da aplicação)
        const gicon = this._ext.iconFor(this._win);
        if (gicon) {
            this._icon.set_child(new St.Icon({gicon, icon_size: ICON_SIZE}));
            return;
        }
        const app = Shell.WindowTracker.get_default().get_window_app(this._win);
        this._icon.set_child(app ? app.create_icon_texture(ICON_SIZE) : null);
    }

    _updateTitle() {
        this._title.text = this._win.get_title() ?? '';
    }

    _update() {
        const w = this._win;
        if (!this._actor || !w.get_compositor_private())
            return;

        const frame = w.get_frame_rect();
        const buffer = w.get_buffer_rect();
        const client = w.frame_rect_to_client_rect(frame);
        const top = client.y - frame.y;
        const max = w.get_maximized() === Meta.MaximizeFlags.BOTH;
        const tiled = w.get_maximized() !== 0 && !max;

        // Só quando a legenda tem a altura do tema XP (outro tema GTK -> nada)
        const expectedTop = max ? CAPTION - BORDER : CAPTION;
        const visible = !w.is_fullscreen() && top === expectedTop;
        this._box.visible = visible;
        if (!visible)
            return;

        const state = w.appears_focused ? 'focused' : 'unfocused';
        // origem da "janela XP" completa (com as bordas) relativa ao ator
        const ox = frame.x - buffer.x - (max ? BORDER : BORDER);
        const oy = frame.y - buffer.y - (max ? BORDER : 0);
        const fullW = frame.width + 2 * BORDER;

        const borders = !max && !tiled;
        const p = this._parts;
        for (const k of ['capLeft', 'capRight', 'left', 'right', 'bottom'])
            p[k].visible = borders;
        if (borders) {
            const sideH = frame.height - CAPTION;
            this._place(p.capLeft, ox, oy, CAPTION_SIDE, CAPTION,
                `background-image: ${this._asset(`caption-left-${state}`)};`);
            this._place(p.capRight, ox + fullW - CAPTION_SIDE, oy, CAPTION_SIDE, CAPTION,
                `background-image: ${this._asset(`caption-right-${state}`)};`);
            this._place(p.left, ox, oy + CAPTION, BORDER, sideH,
                `background-image: ${this._asset(`frame-left-strip-${state}`)}; background-size: ${BORDER}px ${sideH}px;`);
            this._place(p.right, ox + fullW - BORDER, oy + CAPTION, BORDER, sideH,
                `background-image: ${this._asset(`frame-right-strip-${state}`)}; background-size: ${BORDER}px ${sideH}px;`);
            this._place(p.bottom, ox, oy + frame.height, fullW, BORDER,
                `border-image: ${this._asset(`frame-bottom-strip-${state}`)} 0 5 0 5;`);
        }

        this._icon.set_position(ox + ICON_X, oy + ICON_Y);
        this._title.set_position(ox + TEXT_X, oy + this._ext.titleY);
        this._title.set_width(Math.max(0, fullW - TEXT_X - BUTTONS_WIDTH - 4));
        this._title.style_class = w.appears_focused ? 'zxp-title' : 'zxp-title zxp-title-inactive';
    }

    _place(actor, x, y, w, h, style) {
        actor.set_position(x, y);
        actor.set_size(w, Math.max(0, h));
        if (actor._zxpStyle !== style) {
            actor.style = style;
            actor._zxpStyle = style;
        }
    }

    destroy(removeChild = true) {
        if (this._idle)
            GLib.source_remove(this._idle);
        this._idle = 0;
        for (const id of this._signals)
            this._win.disconnect(id);
        this._signals = [];
        if (this._actor && this._actorDestroy)
            this._actor.disconnect(this._actorDestroy);
        if (removeChild && this._box)
            this._box.destroy();
        this._box = null;
        this._actor = null;
        this._ext._frames?.delete(this._win);
    }
}


export class Frames {
    constructor(ext) {
        this._ext = ext;
        this.path = ext.path;
        this.titleY = 9;
        this._frames = new Map();
        this._icons = new Map();     // janela -> ícone escolhido (setIcon)
        this._created = global.display.connect('window-created', (_d, w) => this._track(w));
        for (const actor of global.get_window_actors())
            this._track(actor.meta_window);
    }

    _wants(w) {
        if (!w || w.is_override_redirect())
            return false;
        if (w.get_client_type() !== Meta.WindowClientType.X11)
            return false;
        if (!w.decorated || w.is_client_decorated())
            return false;
        const t = w.get_window_type();
        return t === Meta.WindowType.NORMAL || t === Meta.WindowType.DIALOG ||
               t === Meta.WindowType.MODAL_DIALOG;
    }

    _track(w) {
        if (this._frames.has(w))
            return;
        const attach = () => {
            const actor = w.get_compositor_private();
            if (!actor || this._frames.has(w) || !this._wants(w))
                return false;
            this._frames.set(w, new XpFrame(this, w, actor));
            return true;
        };
        if (!attach()) {
            // o ator ainda não existe logo após window-created
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                attach();
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    iconFor(w) {
        return this._icons.get(w) ?? null;
    }

    // ícone próprio de uma janela na legenda (null: volta ao da aplicação)
    setIcon(w, gicon) {
        const old = this._icons.get(w) ?? null;
        if (old === gicon || (old && gicon && old.equal(gicon)))
            return;
        if (gicon)
            this._icons.set(w, gicon);
        else
            this._icons.delete(w);
        this._frames.get(w)?._updateIcon();
    }

    destroy() {
        global.display.disconnect(this._created);
        for (const f of [...this._frames.values()])
            f.destroy();
        this._frames = null;
        this._icons.clear();
    }
}
