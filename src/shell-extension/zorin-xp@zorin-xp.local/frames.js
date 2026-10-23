/*
 * Zorin XP — Frames
 *
 * On X11 windows with a server-side frame (mutter-x11-frames), mutter 46 only
 * accepts a frame at the top (the right/bottom extents are fixed at 0), and
 * GTK4 does not allow left-aligning the title. The GTK theme draws the
 * caption without the 4 frame columns on each side; this extension adds, as
 * a child of the window actor (it follows moves, animations and overview
 * thumbnails, without catching the mouse):
 *   - the 4 columns on each side of the caption (rounded corners),
 *   - the 4 px left, right and bottom borders,
 *   - the 16×16 icon at (6, 8) and the title from x = 26.
 * Measurements checked to the pixel against real Windows XP captures.
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
// maximized or tiled, the frame's 4 columns are off-screen and XP's icon is
// 2 px from the edge: 2 more here, at the user's wish (and the title with it)
const EDGE_INSET = 2;
const BUTTONS_WIDTH = 73;  // from the minimize button to the right edge
// pieces of the caption sides: 4 frame columns + 8 of the rounded corner
// (which GTK cuts in mutter's frame window; only the top 6 rows)
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
        // (an icon chosen for the window — the page's favicon in IE, see
        // zenIcons.js — or the application's)
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

        // Only when the caption has the XP theme's height (another GTK theme -> nothing)
        const expectedTop = max ? CAPTION - BORDER : CAPTION;
        const visible = !w.is_fullscreen() && top === expectedTop;
        this._box.visible = visible;
        if (!visible)
            return;

        const state = w.appears_focused ? 'focused' : 'unfocused';
        // origin of the whole "XP window" (with the borders) relative to the actor
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

        const inset = borders ? 0 : EDGE_INSET;
        this._icon.set_position(ox + ICON_X + inset, oy + ICON_Y);
        this._title.set_position(ox + TEXT_X + inset, oy + this._ext.titleY);
        this._title.set_width(Math.max(0, fullW - TEXT_X - inset - BUTTONS_WIDTH - 4));
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
        this._icons = new Map();     // window -> chosen icon (setIcon)
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
            // the actor does not exist yet right after window-created
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                attach();
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    iconFor(w) {
        return this._icons.get(w) ?? null;
    }

    // a window's own icon in the caption (null: back to the application's)
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
