/*
 * Geometry of the taskbar buttons as in Windows XP.
 *
 * zorin-taskbar sets in code (inline style) the icon size and the buttons'
 * margins, and draws running indicators; the theme's CSS cannot change
 * them. Here those methods are adjusted at runtime (the system's files are
 * not touched). Measurements taken from real XP captures (30 px bar):
 *   160×30 button with no space between buttons, 16×16 icon at (11, 8),
 *   text from x = 31, no running dots/highlights.
 */
import Clutter from 'gi://Clutter';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {XP_DIR, savedImage, slicedImage} from './images.js';

const TASKBAR_UUID = 'zorin-taskbar@zorinos.com';
const ICON_SIZE = 16;
const ICON_PADDING = 'padding: 8px 4px 6px 11px;';  // 11 + 16 + 4 = 31 px to the text

// Notification area (TrayNotifyHoriz, measured in XP captures): the "show
// hidden icons" arrow (19×20) at the start of the area, centred on the
// curved edge; 16 px icons with an 18 px step from x=19 (ContentMargins);
// when opened, the hidden icons hide again 2 s after the mouse leaves the
// area, as in XP
const TRAY_PAD_L = 19;
const ICON_GAP = 2;
const COLLAPSE_MS = 2000;
// "Show Desktop" (zorin-taskbar's Show Desktop button): invisible and taking
// no space, only a click zone over the bottom right corner
const DESKTOP_HIT_W = 4;
const DESKTOP_STYLE = 'width: 0; padding: 0; margin: 0; border: 0; background: none;';
const SLIDE_MS = 250;   // the hidden icons slide out from the arrow
// network activity: how long (ms, random within the range) each state of the
// monitors' screens lasts — off ~2 s, lit a little longer
const NET_OFF_MS = [1500, 2500];
const NET_ON_MS = [2500, 4000];

// Bytes received and sent by the physical network cards (kernel counters in
// /sys/class/net: no packet capture nor special permissions). The virtual
// ones (lo, docker, bridges, VirtualBox) have no "device" and are left out
let _ifaces = null, _ifacesAt = 0;
const _decoder = new TextDecoder();
function netCounters() {
    const now = GLib.get_monotonic_time();
    if (!_ifaces || now - _ifacesAt > 5000000) {
        _ifacesAt = now;
        _ifaces = [];
        try {
            const en = Gio.File.new_for_path('/sys/class/net').enumerate_children(
                'standard::name', Gio.FileQueryInfoFlags.NONE, null);
            for (let info; (info = en.next_file(null));) {
                const n = info.get_name();
                if (n !== 'lo' && GLib.file_test(`/sys/class/net/${n}/device`, GLib.FileTest.EXISTS))
                    _ifaces.push(n);
            }
            en.close(null);
        } catch (e) {
            return null;
        }
    }
    let rx = 0, tx = 0;
    for (const n of _ifaces) {
        try {
            const [, r] = GLib.file_get_contents(`/sys/class/net/${n}/statistics/rx_bytes`);
            const [, t] = GLib.file_get_contents(`/sys/class/net/${n}/statistics/tx_bytes`);
            rx += Number(_decoder.decode(r));
            tx += Number(_decoder.decode(t));
        } catch (e) {
            // the card disappeared: the list is rebuilt shortly
        }
    }
    return [rx, tx];
}

// XP icon (tray-ico-*.png, extracted from stobject/netshell/sapi/intl/
// irprops/batmeter) for a GNOME status icon; null = XP did not have one
function xpTrayIcon(name) {
    const n = name.replace(/-symbolic$/, '');
    if (n.startsWith('audio-volume-'))
        return n.includes('muted') ? 'volume-muted' : 'volume';
    if (n.startsWith('audio-input-microphone') || n.startsWith('microphone-sensitivity'))
        return 'mic';
    if (n.startsWith('location-services'))
        return 'location';
    if (n.startsWith('bluetooth'))
        return 'bluetooth';
    if (/^network-(wireless|wired|cellular)|^network-offline/.test(n)) {
        if (/acquiring|no-route/.test(n))
            return 'network-busy';
        if (/offline|disconnected|disabled/.test(n))
            return 'network-off';
        return 'network';    // XP uses the two monitors for the wireless network too
    }
    if (n.startsWith('battery')) {
        if (/charging|charged/.test(n))
            return 'battery-ac';     // on mains power: plug with battery
        if (n.includes('missing'))
            return 'battery-missing';
        const m = /battery-level-(\d+)/.exec(n);
        if (m) {
            const v = Number(m[1]);
            return v >= 60 ? 'battery-full' : v >= 30 ? 'battery-half' : v > 10 ? 'battery-low' : 'battery-empty';
        }
        if (n.includes('full'))
            return 'battery-full';
        if (n.includes('good'))
            return 'battery-half';
        if (n.includes('low'))
            return 'battery-low';
        if (/caution|empty/.test(n))
            return 'battery-empty';
        return 'battery-unknown';
    }
    return null;
}

// --- Application icons in colour, as in XP ---------------------------------
// Many apps (Claude, Telegram, LocalSend…) give the notification area a
// monochrome icon. If the icon has no colour, the application's own icon is
// used; the coloured details of the original (e.g. the red dot of unread
// messages) go on top. The ones that already have colour stay as they are.
// Apps whose monochrome icon stays as it is (the colour one does not
// contrast with the notification area's blue)
const TRAY_KEEP_ORIGINAL = ['org.localsend.localsend_app'];

let _iconTheme = null;
function iconPixbuf(gicon, size) {
    try {
        if (gicon instanceof Gio.ThemedIcon) {
            _iconTheme ??= new St.IconTheme();
            const file = _iconTheme.lookup_by_gicon(gicon, size, St.IconLookupFlags.FORCE_SIZE)?.get_filename();
            return file ? GdkPixbuf.Pixbuf.new_from_file_at_size(file, size, size) : null;
        }
        if (gicon instanceof Gio.FileIcon)
            return GdkPixbuf.Pixbuf.new_from_file_at_size(gicon.get_file().get_path(), size, size);
        if (gicon.load) {
            const [stream] = gicon.load(size, null);
            return GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size, size, true, null);
        }
    } catch (e) {
        console.warn(`Zorin XP: ícone da área de notificação: ${e}`);
    }
    return null;
}

const isColored = (r, g, b) => {
    const mx = Math.max(r, g, b);
    return mx > 0 && (mx - Math.min(r, g, b)) / mx > 0.3;
};

// Opaque and coloured pixels: [coloured, opaque]
function colorStats(pb) {
    const px = pb.get_pixels(), n = pb.get_n_channels(), rs = pb.get_rowstride();
    let colored = 0, total = 0;
    for (let y = 0; y < pb.get_height(); y++) {
        for (let x = 0; x < pb.get_width(); x++) {
            const o = y * rs + x * n;
            if (n === 4 && px[o + 3] < 128)
                continue;
            total++;
            if (isColored(px[o], px[o + 1], px[o + 2]))
                colored++;
        }
    }
    return [colored, total];
}

// Application owning the indicator: the one the indicators extension already
// knows or, if not (Flatpak apps), looked up by the icon name and the identifier
const _appCache = new Map();
function trayApp(indicator, gicon) {
    if (indicator?._appInfo?.get_icon?.())
        return indicator._appInfo;
    const cands = [];
    const add = s => {
        if (!s)
            return;
        let c = String(s).replace(/\.(png|svg)$/, '');
        for (let prev; prev !== c;) {
            prev = c;
            c = c.replace(/-symbolic$/, '')
                .replace(/[-_](tray|panel|indicator|mute|muted|attention|unread|active|inactive|dark|light)$/i, '')
                .replace(/_status_icon_\d+$/i, '');
        }
        cands.push(c);
    };
    if (gicon instanceof Gio.ThemedIcon)
        gicon.get_names().forEach(add);
    add(indicator?.id);
    add(indicator?.title);
    const key = cands.join('|');
    if (_appCache.has(key))
        return _appCache.get(key);
    const apps = Gio.AppInfo.get_all();
    let found = null;
    for (const c of cands) {
        const lc = c.toLowerCase();
        if (lc.length < 3)
            continue;
        const id = a => (a.get_id() ?? '').toLowerCase().replace(/\.desktop$/, '');
        for (const match of [
            a => id(a) === lc,
            a => (a.get_startup_wm_class?.() ?? '').toLowerCase() === lc,
            a => (a.get_name() ?? '').toLowerCase() === lc,
            a => lc.length >= 4 && id(a).includes(lc),
        ]) {
            found = apps.find(a => match(a) && a.get_icon());
            if (found)
                break;
        }
        if (found)
            break;
    }
    _appCache.set(key, found);
    return found;
}

// Colour icon for the notification area icon, or null to keep it
function coloredTrayIcon(indicator, gicon) {
    const orig = iconPixbuf(gicon, 16);
    if (!orig)
        return null;
    const [colored, total] = colorStats(orig);
    if (!total || colored / total >= 0.25)
        return null;            // it already has colour
    const app = trayApp(indicator, gicon);
    if (TRAY_KEEP_ORIGINAL.includes((app?.get_id() ?? '').replace(/\.desktop$/, '')))
        return null;
    const appIcon = app?.get_icon();
    if (!appIcon)
        return null;
    if (!colored)
        return appIcon;
    // coloured details of the original on top of the application's icon
    let base = iconPixbuf(appIcon, 16);
    if (!base)
        return appIcon;
    if (!base.get_has_alpha())
        base = base.add_alpha(false, 0, 0, 0);
    const out = base.get_pixels(), bn = base.get_n_channels(), brs = base.get_rowstride();
    const px = orig.get_pixels(), n = orig.get_n_channels(), rs = orig.get_rowstride();
    for (let y = 0; y < 16; y++) {
        for (let x = 0; x < 16; x++) {
            const o = y * rs + x * n;
            if ((n === 4 && px[o + 3] < 128) || !isColored(px[o], px[o + 1], px[o + 2]))
                continue;
            const d = y * brs + x * bn;
            out[d] = px[o];
            out[d + 1] = px[o + 1];
            out[d + 2] = px[o + 2];
            out[d + 3] = 255;
        }
    }
    const composed = GdkPixbuf.Pixbuf.new_from_bytes(new GLib.Bytes(out), GdkPixbuf.Colorspace.RGB,
        true, 8, 16, 16, brs);
    const sum = GLib.compute_checksum_for_data(GLib.ChecksumType.MD5, out);
    return Gio.FileIcon.new(Gio.File.new_for_path(savedImage(`trayapp-${sum}`, composed)));
}

// Application icon at 16 px (the original size, at the user's request on
// 2026-10-13); the gap between them comes from TRAY_APP_HPAD
const TRAY_APP_SIZE = 16;
// margin on each side of the application icons: 2 px more between them (20 px step)
const TRAY_APP_HPAD = 1;
function paddedTrayIcon(gicon) {
    // (symbolic ones are recoloured by St: loaded separately they lost their colour)
    if (gicon instanceof Gio.ThemedIcon && gicon.get_names().some(n => n.endsWith('-symbolic')))
        return null;
    const pb = iconPixbuf(gicon, TRAY_APP_SIZE);
    if (!pb)
        return null;
    const canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, true, 8, 16, 16);
    canvas.fill(0);
    const src = pb.get_has_alpha() ? pb : pb.add_alpha(false, 0, 0, 0);
    const off = (16 - TRAY_APP_SIZE) / 2;
    src.copy_area(0, 0, TRAY_APP_SIZE, TRAY_APP_SIZE, canvas, off, off);
    const sum = GLib.compute_checksum_for_data(GLib.ChecksumType.MD5, canvas.get_pixels());
    return Gio.FileIcon.new(Gio.File.new_for_path(savedImage(`trayapp${TRAY_APP_SIZE}-${sum}`, canvas)));
}

// Background, arrow and hidden icons of a panel's notification area. The
// application icons (#panelRight) hide behind the arrow; the system ones
// (quick settings) and the clock are always visible.
class XpTray {
    constructor(p) {
        this._p = p;
        this._right = p._rightBox ?? p.panel?._rightBox;
        this._system = p.statusArea?.quickSettings ?? null;
        this._date = p.statusArea?.dateMenu ?? null;
        this._expanded = false;
        this._touched = new Set();
        this._watched = new Set();
        this._styles = [];
        this._timer = 0;
        this._icons = new Set();
        this._boxes = new Set();
        this._appIcons = new Set();

        // The background goes in zorin-taskbar's own inner panel (transparent,
        // full width): an actor added to the panel would not be laid out
        this._panel = p.panel;
        // (zorin-taskbar's panel only lays out the children it knows: this one is
        // placed by hand in _syncBg; touching only it is cheap, unlike
        // changing the panel's style, which restyles the whole bar)
        // (leftovers from an earlier time that was not torn down: out)
        for (const c of this._panel.get_children()) {
            if (c.name === 'zxpTrayBg')
                c.destroy();
        }
        for (const c of this._right.get_children()) {
            if (c.has_style_class_name?.('zxp-chevron'))
                c.destroy();
        }
        this._bg = new St.Widget({reactive: false, name: 'zxpTrayBg'});
        this._panel.insert_child_at_index(this._bg, 0);
        this._chevron = new St.Button({
            style_class: 'zxp-chevron',
            reactive: true,
            can_focus: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
            accessible_name: 'Mostrar ícones ocultos',
        });
        this._chevron.connect('clicked', () => this._setExpanded(!this._expanded));
        this._right.insert_child_at_index(this._chevron, 0);
        this._right.connectObject(
            'child-added', (_b, c) => this._onAdded(c),
            'child-removed', (_b, c) => {
                this._touched.delete(c);
                this._apply();
            },
            'notify::allocation', () => this._syncBg(), this);
        this._panel.connectObject(
            'notify::allocation', () => {
                this._syncBg();
                this._syncDesktop();
            },
            'notify::style', () => this._syncBg(), this);
        for (const c of this._right.get_children())
            this._onAdded(c);

        // system icons with XP's
        if (this._system?._indicators)
            this._hookIcons(this._system._indicators);

        // system icons in a row, with XP's step, and 2 px before the clock
        // (2 px of left margin — padding was ignored on this button: the
        // system icons fill the 16 px, without the transparent margin of the
        // application ones; this way the visible gap at the join matches the others)
        this._style(this._system, '-natural-hpadding: 0; -minimum-hpadding: 0; padding: 0; margin-left: 2px;');
        this._style(this._system?.container, `margin-right: ${ICON_GAP}px;`);
        // -natural-hpadding does not invalidate the button's cached width (there
        // were 9 px on each side between the application and system icons)
        this._system?.queue_relayout();
        // clock as in Portuguese XP: "0:14", without the hour's leading zero and
        // with a normal colon (GNOME writes "00‎∶14": an invisible
        // direction mark and "∶", U+2236, which Tahoma does not even have and
        // which came from another, taller font)
        const clock = this._date?._clockDisplay;
        if (clock) {
            const fix = () => {
                const t = clock.text.replace(/[\u200e\u200f]/g, '').replace(/\u2236/g, ':')
                    .replace(/(^|\s)0(\d:)/, '$1$2');
                if (t !== clock.text)
                    clock.text = t;
            };
            clock.connectObject('notify::text', fix, this);
            fix();
        }
        this._apply();
    }

    // Swaps GNOME's status icons for XP's, also in indicators added later and
    // every time GNOME changes the icon
    _hookIcons(actor) {
        if (actor instanceof St.Icon) {
            this._hookIcon(actor);
            return;
        }
        if (!this._boxes.has(actor)) {
            this._boxes.add(actor);
            actor.connectObject('child-added', (_a, c) => this._hookIcons(c), this);
        }
        for (const c of actor.get_children())
            this._hookIcons(c);
    }

    _hookIcon(icon) {
        if (this._icons.has(icon))
            return;
        this._icons.add(icon);
        const sync = () => {
            const g = icon.gicon;
            if (!(g instanceof Gio.ThemedIcon))
                return;
            const key = xpTrayIcon(g.get_names()[0] ?? '');
            if (!key)
                return;
            icon._zxpOrig = g;
            icon.set_style('-st-icon-style: regular;');   // in colour, not recoloured
            if (key === 'network') {
                // connected: the screens light up with the traffic (see _netTick)
                this._netIcon = icon;
                this._setIcon(icon, icon._zxpNet ?? 'network');
                if (!this._netTimer)
                    this._scheduleNet();
                return;
            }
            if (this._netIcon === icon)
                this._netIcon = null;
            this._setIcon(icon, key);
        };
        icon.connectObject('notify::gicon', sync, this);
        sync();
    }

    // Monochrome application icons -> the application's colour icon, all at 16 px
    _hookAppIcon(button) {
        const icon = button._icon;
        if (this._appIcons.has(icon))
            return;
        this._appIcons.add(icon);
        const sync = () => {
            const g = icon.gicon;
            if (!g || g === icon._zxpColor)
                return;
            icon._zxpTrayOrig = g;
            // the indicators extension wraps the icons in an EmblemedIcon (and calls
            // get_icon() on the current one): unwrap and wrap again
            const inner = g instanceof Gio.EmblemedIcon ? g.get_icon() : g;
            const base = coloredTrayIcon(button._indicator, inner) ?? inner;
            const color = paddedTrayIcon(base) ?? (base !== inner ? base : null);
            if (color) {
                const wrapped = new Gio.EmblemedIcon({gicon: color});
                if (g instanceof Gio.EmblemedIcon)
                    g.get_emblems().forEach(e => wrapped.add_emblem(e));
                icon._zxpColor = wrapped;
                icon.gicon = wrapped;
            }
        };
        icon.connectObject('notify::gicon', sync, this);
        sync();
    }

    _setIcon(icon, key) {
        icon.gicon = Gio.FileIcon.new(Gio.File.new_for_path(`${XP_DIR}/tray-ico-${key}.png`));
    }

    _scheduleNet(key = 'network') {
        const [min, max] = key === 'network' ? NET_OFF_MS : NET_ON_MS;
        const ms = min + Math.floor(Math.random() * (max - min));
        this._netTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._netTimer = 0;
            this._netTick();
            return GLib.SOURCE_REMOVE;
        });
    }

    // As in XP, the front screen lights up when the computer sends and the
    // back one when it receives. With today's continuous traffic both would
    // always be lit: while there is traffic in one direction, the matching
    // screen lights up at random (more often in the direction with more
    // traffic), without repeating the previous state; without traffic they
    // stay off
    _netTick() {
        const icon = this._netIcon;
        if (!icon) {
            this._netLast = null;
            return;
        }
        const cur = netCounters();
        let key = 'network';
        if (cur && this._netLast) {
            const dRx = Math.max(0, cur[0] - this._netLast[0]);
            const dTx = Math.max(0, cur[1] - this._netLast[1]);
            const total = dRx + dTx;
            if (total > 0) {
                const pRx = dRx ? 0.25 + 0.5 * dRx / total : 0;
                const pTx = dTx ? 0.25 + 0.5 * dTx / total : 0;
                const keyOf = (rx, tx) => rx && tx ? 'network-txrx' : tx ? 'network-tx' : rx ? 'network-rx' : 'network';
                // draws until a state different from the previous one comes up (off also
                // counts: that is what gives the blinking effect)
                for (let i = 0; i < 6 && (i === 0 || key === icon._zxpNet); i++)
                    key = keyOf(Math.random() < pRx, Math.random() < pTx);
            }
        }
        this._netLast = cur;
        if (key !== icon._zxpNet) {
            icon._zxpNet = key;
            this._setIcon(icon, key);
        }
        this._scheduleNet(key);
    }

    _style(actor, css) {
        if (!actor)
            return;
        const old = actor.get_style();
        this._styles.push([actor, old]);
        actor.set_style(`${old ?? ''}${css}`);
    }

    _items() {
        return this._right.get_children().filter(c => c !== this._chevron);
    }

    _onAdded(c) {
        if (c === this._chevron)
            return;
        // the arrow is always the first element
        if (this._right.get_child_at_index(0) !== this._chevron)
            this._right.set_child_at_index(this._chevron, 0);
        const button = c.get_first_child?.() ?? c;
        if (!this._watched.has(button)) {
            this._watched.add(button);
            button.connectObject('notify::visible', () => this._apply(), this);
            // the application indicators (compact mode) force 10 px on each side in
            // code; here TRAY_APP_HPAD (20 px step)
            if (button.has_style_class_name?.('panel-button')) {
                button._zxpStyle = button.get_style();
                const fix = () => {
                    const st = button.get_style() ?? '';
                    const pad = `-natural-hpadding: ${TRAY_APP_HPAD}px; -minimum-hpadding: ${TRAY_APP_HPAD}px;`;
                    if (st.includes(pad))
                        return;
                    button.set_style(`${st.replace(/-(natural|minimum)-hpadding:[^;]*;?/g, '')}${pad}`);
                    button.queue_relayout();  // (cached width, see above)
                };
                button.connectObject('notify::style', fix, this);
                fix();
            }
            if (button._indicator && button._icon instanceof St.Icon)
                this._hookAppIcon(button);
        }
        if (!this._watched.has(c)) {
            // GNOME shows the container again when it moves to another panel
            this._watched.add(c);
            c.connectObject('notify::visible', () => this._apply(), this);
        }
        this._apply();
    }

    // Hides/shows the application icons (each one's container is only visible
    // if the arrow is open and the icon exists: empty containers took 2 px).
    // The arrow only appears if there is some icon to hide; without it, the
    // area starts 19 px before the first system icon
    _apply() {
        if (this._applying)
            return;
        this._applying = true;
        const items = this._items();
        let any = false;
        for (const c of items) {
            const shown = (c.get_first_child?.() ?? c).visible;
            any ||= shown;
            const want = this._expanded && shown;
            this._touched.add(c);
            if (c.visible !== want && !this._sliding)
                c.visible = want;
        }
        this._chevron.visible = any;
        this._right.set_style(`padding-left: ${any ? 0 : TRAY_PAD_L}px; spacing: 0;`);
        if (this._expanded)
            this._chevron.add_style_class_name('zxp-open');
        else
            this._chevron.remove_style_class_name('zxp-open');
        this._applying = false;
        this._syncBg();
    }

    _setExpanded(expanded) {
        this._expanded = expanded;
        this._slide(expanded);
        this._apply();
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        if (!expanded)
            return;
        // closes 2 s after the mouse leaves the area (and with no menus open)
        let since = null;
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            if (this._pointerInside() || this._menuOpen()) {
                since = null;
            } else {
                since ??= GLib.get_monotonic_time();
                if (GLib.get_monotonic_time() - since >= COLLAPSE_MS * 1000) {
                    this._timer = 0;
                    this._setExpanded(false);
                    return GLib.SOURCE_REMOVE;
                }
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    // As in XP (compared with a recording of XP's area): when opening, the
    // icons are in place at once and the arrow — with the edge of the light
    // background — slides left and uncovers them; when closing, the arrow and
    // the icons slide right together and vanish at the edge of the system
    // icons. Nothing shrinks or stretches: only translation and clipping.
    _slide(expanded) {
        this._stopSlide();
        const items = this._items().filter(c => (c.get_first_child?.() ?? c).visible);
        if (!items.length)
            return;
        this._sliding = true;
        const chev = this._chevron;
        const finish = () => {
            for (const c of items) {
                c.translation_x = 0;
                c.remove_clip();
                if (!expanded)
                    c.hide();
            }
            chev.translation_x = 0;
            this._slideItems = null;
            this._sliding = false;
            this._apply();
        };
        const run = (from, to, clip) => {
            this._slideItems = items;
            const update = () => {
                clip(chev.translation_x);
                this._syncBg();
            };
            chev.translation_x = from;
            update();
            chev.connectObject('notify::translation-x', update, this);
            chev.ease({
                translation_x: to,
                duration: SLIDE_MS,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onStopped: () => {
                    chev.disconnectObject(this);
                    finish();
                },
            });
        };

        if (expanded) {
            // shows the icons and waits for the final layout to know the distance;
            // until then they are invisible
            for (const c of items) {
                c.opacity = 0;
                c.show();
            }
            // (already laid out, still before drawing: no jumps)
            const id = global.stage.connect('before-paint', () => {
                global.stage.disconnect(id);
                const dist = this._right.width - chev.width;
                for (const c of items)
                    c.opacity = 255;
                // only what is to the right of the arrow is visible
                run(dist, 0, t => {
                    const edge = t + chev.width;
                    for (const c of items) {
                        const left = Math.min(c.width, Math.max(0, edge - c.x));
                        c.set_clip(left, 0, c.width - left, c.height);
                    }
                });
            });
            global.stage.queue_redraw();
        } else {
            const end = this._right.width;
            const dist = end - chev.width;
            // the icons follow the arrow and are clipped at the edge of the area
            run(0, dist, t => {
                for (const c of items) {
                    c.translation_x = t;
                    const w = Math.min(c.width, Math.max(0, end - (c.x + t)));
                    c.set_clip(0, 0, w, c.height);
                }
            });
        }
    }

    _stopSlide() {
        this._chevron.remove_all_transitions();
        this._chevron.disconnectObject(this);
        for (const c of this._slideItems ?? []) {
            c.translation_x = 0;
            c.opacity = 255;
            c.remove_clip();
        }
        this._chevron.translation_x = 0;
        this._slideItems = null;
        this._sliding = false;
    }

    _pointerInside() {
        const [x, y] = global.get_pointer();
        const [rx, ry] = this._right.get_transformed_position();
        const [px] = this._panel.get_transformed_position();
        return x >= rx && x < px + this._panel.width && y >= ry && y < ry + this._panel.height;
    }

    _menuOpen() {
        return this._items().some(c => (c.get_first_child?.() ?? c).menu?.isOpen);
    }

    // Background (TaskbarTray) from the start of #panelRight to the right of the
    // panel, composed at the exact size (St's border-image distorts the slices)
    // in its own actor below the icons; during the animation the edge follows
    // the arrow
    _syncBg() {
        const box = this._right.get_allocation_box();
        const w = Math.round(this._panel.width), h = Math.round(this._panel.height);
        const x = Math.round(box.x1 + this._chevron.translation_x);
        if (!Number.isFinite(x) || w < 44 || h <= 0 || x >= w - 44) {
            this._bg.hide();
            return;
        }
        if (x !== this._bgX || w !== this._bgW || h !== this._bgH) {
            let img;
            try {
                img = slicedImage('tray', w - x, h, [0, 10, 0, 34]);
            } catch (e) {
                console.error(`Zorin XP: área de notificação: ${e}`);
                return;
            }
            this._bgX = x;
            this._bgW = w;
            this._bgH = h;
            this._bg.set_style(`background-image: url("file://${img}"); background-size: auto;`);
        }
        this._bg.show();
        this._bg.allocate(new Clutter.ActorBox({x1: x, y1: 0, x2: w, y2: h}));
    }

    // The button is still zorin-taskbar's (it handles the click); here it gets
    // no width in the layout (it does not push the clock), no line nor icon,
    // and it is placed by hand over the panel's right corner
    _syncDesktop() {
        const b = this._p._showDesktopButton;
        if (!b)
            return;
        if (this._desktop !== b) {
            this._desktop?.disconnectObject(this);
            this._desktop = b;
            const strip = () => {
                if (b.icon?.get_parent() === b)
                    b.remove_child(b.icon);
                if (b.get_style() !== DESKTOP_STYLE)
                    b.set_style(DESKTOP_STYLE);
            };
            // (zorin-taskbar lays it out again with width 0 whenever it rearranges
            // the panel: put it back right after)
            b.connectObject('notify::style', strip, 'child-added', strip,
                'notify::allocation', () => this._placeDesktop(), this);
            strip();
        }
        this._panel.set_child_above_sibling(b, null);
        this._placeDesktop();
    }

    _placeDesktop() {
        const b = this._desktop;
        const w = Math.round(this._panel.width), h = Math.round(this._panel.height);
        if (!b || w <= DESKTOP_HIT_W || h <= 0)
            return;
        const box = b.get_allocation_box();
        if (box.x1 === w - DESKTOP_HIT_W && box.x2 === w && box.y1 === 0 && box.y2 === h)
            return;
        b.allocate(new Clutter.ActorBox({x1: w - DESKTOP_HIT_W, y1: 0, x2: w, y2: h}));
    }

    destroy() {
        // Each step separately: when the screen locks, zorin-taskbar destroys the
        // "Show Desktop" button (and other actors) before this runs; an error
        // halfway left the arrow and the background on the panel, and after
        // unlocking another one came on top (duplicated arrow)
        const step = fn => {
            try {
                fn();
            } catch (e) {
                console.debug(`Zorin XP: área de notificação: ${e}`);
            }
        };
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        if (this._netTimer)
            GLib.source_remove(this._netTimer);
        this._netTimer = 0;
        this._netIcon = null;
        step(() => this._chevron.destroy());
        step(() => this._bg.destroy());
        if (this._desktop) {
            const desktop = this._desktop;
            this._desktop = null;
            step(() => desktop.disconnectObject(this));
            step(() => desktop.set_style(null));
            step(() => this._p._setShowDesktopButtonStyle?.());
        }
        step(() => this._right.disconnectObject(this));
        step(() => this._p.disconnectObject(this));
        for (const a of this._boxes)
            step(() => a.disconnectObject(this));
        for (const icon of this._appIcons) {
            step(() => {
                icon.disconnectObject(this);
                if (icon._zxpTrayOrig && icon.gicon === icon._zxpColor)
                    icon.gicon = icon._zxpTrayOrig;
                delete icon._zxpColor;
                delete icon._zxpTrayOrig;
            });
        }
        for (const icon of this._icons) {
            step(() => {
                icon.disconnectObject(this);
                if (icon._zxpOrig) {
                    icon.set_style(null);
                    icon.gicon = icon._zxpOrig;
                    delete icon._zxpOrig;
                }
            });
        }
        for (const b of this._watched) {
            step(() => {
                b.disconnectObject(this);
                if (b._zxpStyle !== undefined) {
                    b.set_style(b._zxpStyle);
                    delete b._zxpStyle;
                }
            });
        }
        for (const c of this._touched)
            step(() => c.show());
        this._touched.clear();
        const clock = this._date?._clockDisplay;
        if (clock) {
            step(() => {
                clock.disconnectObject(this);
                clock.text = this._date._clock?.clock ?? clock.text;
            });
        }
        for (const [actor, old] of this._styles.reverse())
            step(() => actor.set_style(old));
        step(() => this._right.set_style(null));
        step(() => this._panel.disconnectObject(this));
        step(() => {
            const style = this._panel.get_style() ?? '';
            if (style.includes('/*zxp*/'))
                this._panel.set_style(style.slice(0, style.indexOf('/*zxp*/')));
        });
    }
}

export class TaskbarTweaks {
    constructor(ext) {
        this._ext = ext;
        this._patches = [];
        this._trays = new Map();
        this._load().catch(e => console.error(`Zorin XP: barra de tarefas: ${e}`));
    }

    async _load() {
        const tb = Main.extensionManager.lookup(TASKBAR_UUID);
        if (!tb)
            return;
        // Same URL the extension loader uses -> same module instances
        const appIcons = await import(`file://${tb.path}/appIcons.js`);
        const taskbar = await import(`file://${tb.path}/taskbar.js`);
        if (this._destroyed)
            return;

        const AppIcon = appIcons.TaskbarAppIcon;
        const Taskbar = taskbar.Taskbar;

        this._patch(AppIcon.prototype, '_setAppIconPadding', function () {
            this.set_style('padding: 0;');
            this._iconContainer.set_style(ICON_PADDING);
        });
        // The active window's button "pressed" (xp.css: .focused). With ungrouped
        // windows zorin-taskbar only sets .focused in grouped mode.
        const setIconStyle = AppIcon.prototype._setIconStyle;
        this._patch(AppIcon.prototype, '_setIconStyle', function (isFocused) {
            setIconStyle.call(this, isFocused);
            if (!this._isGroupApps) {
                if (isFocused)
                    this.add_style_class_name('focused');
                else
                    this.remove_style_class_name('focused');
            }
        });
        this._patch(AppIcon.prototype, '_getRunningIndicatorSize', () => 0);
        this._patch(AppIcon.prototype, '_drawRunningIndicator', () => {});
        this._patch(Taskbar.prototype, '_adjustIconSize', function () {
            if (this.iconSize === ICON_SIZE && this._zxpSized)
                return;
            this._zxpSized = true;
            this.iconSize = ICON_SIZE;
            for (const c of this._getTaskbarIcons().concat([this._showAppsIcon]))
                c.child?._delegate?.icon?.setIconSize(ICON_SIZE);
        });
        this._watchTaskbar();
        // ZXP_DEBUG=1 in the Shell's environment or ~/.cache/zorin-xp-debug: actor
        // tree in the journal
        if (GLib.getenv('ZXP_DEBUG') ||
            GLib.file_test(`${GLib.get_user_cache_dir()}/zorin-xp-debug`, GLib.FileTest.EXISTS))
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
                this.dumpPanels();
                return GLib.SOURCE_REMOVE;
            });
    }

    _patch(proto, name, impl) {
        const orig = proto[name];
        if (typeof orig !== 'function')
            return;
        proto[name] = impl;
        this._patches.push([proto, name, orig]);
    }

    // Diagnostics: the panel's actor tree in the journal (journalctl -o cat | grep ZXP)
    dumpPanels() {
        const walk = (a, d) => {
            if (d > 9 || !a)
                return;
            const cls = a.get_style_class_name?.() ?? '';
            const name = a.get_name?.() ?? '';
            const [w, h] = a.get_size();
            const [x, y] = a.get_transformed_position();
            let box = '';
            const node = a.get_theme_node?.();
            if (node) {
                const pad = [St.Side.TOP, St.Side.RIGHT, St.Side.BOTTOM, St.Side.LEFT].map(sd => node.get_padding(sd));
                box = ` pad=${pad.join(',')} margin=${a.margin_left},${a.margin_right} vis=${a.visible}`;
                if (a._natHPadding !== undefined)
                    box += ` hpad=${a._natHPadding}`;
            }
            console.log(`ZXP ${'  '.repeat(d)}${a.constructor.name}${name ? '#' + name : ''}${cls ? '.' + cls.replace(/ /g, '.') : ''} ` +
                `${Math.round(x)},${Math.round(y)} ${Math.round(w)}x${Math.round(h)}${box} style="${a.get_style?.() ?? ''}"`);
            for (const c of a.get_children())
                walk(c, d + 1);
        };
        for (const p of global.zorinTaskbar?.panels ?? [])
            walk(p, 0);
    }

    // zorin-taskbar may get enabled after this extension (its enable is
    // asynchronous) and it creates a new global.zorinTaskbar, and new
    // panels, every time it is (re)enabled: connect to the current object and
    // follow the changes
    _watchTaskbar() {
        const attach = () => {
            const zt = global.zorinTaskbar;
            if (zt && zt !== this._zt) {
                if (this._zt && this._panelsId)
                    this._zt.disconnect(this._panelsId);
                this._zt = zt;
                this._panelsId = zt.connect('panels-created', () => this._refresh());
            }
            this._refresh();
        };
        Main.extensionManager.connectObject('extension-state-changed', (_m, ext) => {
            if (ext?.uuid === TASKBAR_UUID)
                attach();
        }, this);
        attach();
    }

    _addTray(p) {
        if (this._trays.has(p) || !(p._rightBox ?? p.panel?._rightBox))
            return;
        try {
            this._trays.set(p, new XpTray(p));
        } catch (e) {
            console.error(`Zorin XP: área de notificação: ${e}\n${e.stack}`);
        }
    }

    _refresh() {
        // panels that no longer exist (zorin-taskbar recreated them)

        const panels = global.zorinTaskbar?.panels ?? [];
        for (const [p, tray] of this._trays) {
            if (!panels.includes(p)) {
                try {
                    tray.destroy();
                } catch (e) {
                    console.debug(`Zorin XP: área de notificação: ${e}`);
                }
                this._trays.delete(p);
            }
        }
        for (const p of panels) {
            if (!this._destroyed && p)
                this._addTray(p);
            const t = p?.taskbar;
            if (!t)
                continue;
            t._zxpSized = false;
            t._adjustIconSize?.();
            for (const c of t._getTaskbarIcons?.() ?? []) {
                const icon = c.child?._delegate;
                icon?._setAppIconPadding?.();
                icon?._displayProperIndicator?.();
            }
        }
    }

    destroy() {
        this._destroyed = true;
        Main.extensionManager.disconnectObject(this);
        if (this._zt && this._panelsId)
            this._zt.disconnect(this._panelsId);
        this._zt = null;
        for (const tray of this._trays.values())
            tray.destroy();
        this._trays.clear();
        for (const [proto, name, orig] of this._patches.reverse())
            proto[name] = orig;
        this._patches = [];
        this._refresh();
    }
}
