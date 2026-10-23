/*
 * Zorin's Start menu with the look of the Windows XP Start menu.
 *
 * Keeps the content and behaviour of zorin-menu (the "ALL" layout:
 * categories + search on the left, places and shortcuts on the right) and
 * rearranges it like XP (measurements from real captures, 380 px menu):
 *   ┌ StartUserPanel band (64 px): 48 px picture at (9,9) with the
 *   │ UserTileBackground frame at (1,1), name in Franklin Gothic Medium 14 pt at x 67
 *   ├ left column 190 px (ProgList) │ right column 190 px (PlacesList)
 *   └ StartPanelLogoff band (41 px): hidden search (type to search); "Terminar sessão" and
 *     "Encerrar" at the same distance from the right as in XP (x 185 and 302 of 380)
 * The user from the right column moves to the top band; Zorin's session
 * buttons give way to XP's; the search goes to the bottom band.
 * Icons, categories and "Todos os programas" stay as in Zorin.
 */
import AccountsService from 'gi://AccountsService';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {XP_DIR, slicedImage} from './images.js';
import {showEndSession, LOGOUT, SHUTDOWN} from './endSession.js';

const MENU_UUID = 'zorin-menu@zorinos.com';

// closes the Start menu (every monitor) at once, without animation
export function closeStartMenus() {
    const buttons = Main.extensionManager.lookup(MENU_UUID)?.stateObj?.menuButtons ?? [];
    for (const b of buttons) {
        if (b?._menu?.isOpen)
            b._menu.close(BoxPointer.PopupAnimation.NONE);
    }
}
const HEADER_H = 64;
const FOOTER_H = 41;
// Widths equal to tools/builders/shelltheme.py's (XP had 380 = 190 + 190)
const START_W = 380, LEFT_W = 190, RIGHT_W = START_W - LEFT_W;
// Bottom band buttons as in XP: icons at x=184 and 301 (of 380)
const LOGOFF_X = START_W - 196, SHUTDOWN_X = START_W - 79;
const SEARCH_X = 8, SEARCH_W = 150, SEARCH_H = 20;
const SEP_H = 9;  // XP separators: 9 px with the 2 px line
// Left column (measurements from XP captures, counting from the top of the
// bottom band F): separator line at F-36, "Todos os programas" (16×24 arrow
// and highlight) from F-29 to F-6, 5 px of margin below (ProgList ContentMargins)
const LEFT_PAD_T = 6, LEFT_PAD_B = 5;
const LEFT_SEP_H = 10;  // separator above "Todos os programas": 3 + line 2 + 5
const SHADOW_W = 5;     // XP shadow: 5 px to the right and below
const ARROW_H = 17;     // XP scrollbar arrows (17×17)

// Diagnostics: ~/.cache/zorin-xp-debug exists -> log in the journal (journalctl)
const debug = msg => {
    if (GLib.file_test(`${GLib.get_user_cache_dir()}/zorin-xp-debug`, GLib.FileTest.EXISTS))
        console.log(`ZXP ${msg}`);
};

export class StartMenuTweaks {
    constructor(ext) {
        this._ext = ext;
        this._patches = [];
        this._load().catch(e => console.error(`Zorin XP: menu Iniciar: ${e}`));
    }

    async _load() {
        const menu = Main.extensionManager.lookup(MENU_UUID);
        if (!menu)
            return;
        const mod = await import(`file://${menu.path}/layouts/standardLayout.js`);
        this._misc = await import(`file://${menu.path}/widgets/miscMenuItems.js`);
        const base = await import(`file://${menu.path}/widgets/baseMenuItem.js`);
        if (this._destroyed)
            return;
        const proto = mod.StandardLayout.prototype;
        const self = this;

        this._patch(proto, '_loadLayout', function (orig) {
            orig.call(this);
            try {
                self._xpify(this);
            } catch (e) {
                console.error(`Zorin XP: menu Iniciar: ${e}\n${e.stack}`);
            }
        });
        // Nothing preselected: Zorin gives the keyboard focus to the first item
        // when the menu opens (and to the first program when a category
        // opens), which highlights it and makes the list jump to it. As in XP,
        // the focus stays on the menu itself until the keyboard is used: the
        // first arrow selects the first item (BaseLayout._onKeyPress) and
        // typing starts the search. Opening a category with the keyboard
        // keeps Zorin's behaviour.
        // The highlight follows the mouse: when leaving an item, the keyboard
        // focus Zorin gave it on hover goes back to the menu. Otherwise the
        // item stays "targeted": when a grab ends (e.g. the scrollbar
        // arrows') GNOME gives it the focus back and Zorin highlights it and
        // scrolls the list to it
        this._patch(base.BaseMenuItem.prototype, '_onHover', function (orig, ...args) {
            orig.call(this, ...args);
            if (this.hover || !this.has_key_focus())
                return;
            for (let a = this.get_parent(); a; a = a.get_parent()) {
                if (a._zxp) {
                    global.stage.set_key_focus(a);
                    break;
                }
            }
        });
        this._patch(proto, 'reset', function (orig) {
            orig.call(this);
            if (this._zxp)
                global.stage.set_key_focus(this);
        });
        // With the mouse, the list does not get the focus either: Zorin would focus
        // the first program and the list would slide to the top (when reopening
        // the same category, which keeps the position where it was)
        this._patch(proto, '_onSelectCategory', function (orig, ...args) {
            const type = Clutter.get_current_event()?.type();
            const keyboard = type === Clutter.EventType.KEY_PRESS || type === Clutter.EventType.KEY_RELEASE;
            const apps = this._appsSection;
            if (!this._zxp || keyboard || !apps) {
                orig.call(this, ...args);
                return;
            }
            apps.grab_key_focus = () => {};
            try {
                orig.call(this, ...args);
            } finally {
                delete apps.grab_key_focus;
            }
            global.stage.set_key_focus(this);
        });
        // The arrows start at the first item, as in XP. In a search, Zorin
        // marks the first result as the default (for Enter) without showing
        // it here, and its first arrow went past it: to the next result, a
        // group title or "Voltar". ↑ with nothing selected went round to
        // "Terminar sessão".
        this._patch(proto, '_onKeyPress', function (orig, actor, event) {
            if (!this._zxp)
                return orig.call(this, actor, event);
            const symbol = event.get_key_symbol();
            const down = symbol === Clutter.KEY_Down || symbol === Clutter.KEY_KP_Down;
            const up = symbol === Clutter.KEY_Up || symbol === Clutter.KEY_KP_Up;
            if (!down && !up)
                return orig.call(this, actor, event);
            const top = this._searchResults?.get_parent() ? this._searchResults.getTopResult() : null;
            if (top && this._searchEntry?.has_key_focus()) {
                top.remove_style_pseudo_class('focus');
                top.grab_key_focus();
                return Clutter.EVENT_STOP;
            }
            if (up && global.stage.key_focus === this) {
                if (this._categoriesSection?.visible)
                    this._categoriesSection.grab_key_focus();
                else if (this._appsSection?.visible)
                    this._appsSection.grab_key_focus();
                else
                    this._placesSection?.grab_key_focus();
                return Clutter.EVENT_STOP;
            }
            return orig.call(this, actor, event);
        });
        // The search's group titles ("Janelas abertas", "Software") are not
        // stops for the arrows (the items move the focus themselves, through
        // St's focus manager); hover and click still open them
        this._patch(base.BaseMenuItem.prototype, '_init', function (orig, ...args) {
            orig.call(this, ...args);
            if (this.constructor.name === 'ProviderInfo')
                this.can_focus = false;
        });
        this._patch(proto, '_availableHeight', function (orig) {
            const h = orig.call(this);
            return this._zxp ? h - HEADER_H - FOOTER_H : h;
        });
        this._patch(proto, 'updateHeight', function (orig) {
            if (!this._zxp) {
                orig.call(this);
                return;
            }
            // height calculated from scratch (this.height would return the height of
            // the previous opening and the menu would grow on every opening)
            const available = this._availableHeight();
            const bodyH = this._sidebar.updateHeight(available);
            // everything with a fixed height: the body cannot shrink/stretch with the
            // content (otherwise the bottom band moves up and down)
            this._zxpBody?.set_height(bodyH);
            this.set_height(bodyH + HEADER_H + FOOTER_H + SHADOW_W);
            // shadow: image of the menu's exact size + 5 px (see _xpify)
            const shadow = slicedImage('start-shadow', START_W + SHADOW_W,
                bodyH + HEADER_H + FOOTER_H + SHADOW_W, [15, SHADOW_W, SHADOW_W, 10]);
            this.set_style(`padding: 0 ${SHADOW_W}px ${SHADOW_W}px 0; ` +
                `background-image: url("file://${shadow}"); background-position: 0 0; ` +
                'background-repeat: no-repeat;');
            debug(`updateHeight: disponível=${available} altura=${this.height}`);
            // the popup content has the Zorin theme's padding: cancel it (inline)
            for (let a = this.get_parent(); a; a = a.get_parent()) {
                if (a.has_style_class_name?.('popup-menu-content') ||
                    a.has_style_class_name?.('popup-menu-section'))
                    a.set_style('padding: 0; margin: 0; spacing: 0; border-width: 0;');
                if (a.has_style_class_name?.('popup-menu-boxpointer')) {
                    // no arrow nor margins (the Zorin theme gives 4 px rise and margin-bottom 1.75em)
                    a.set_style('margin: 0; -arrow-rise: 0; -arrow-base: 0; ' +
                        '-arrow-border-width: 0; -arrow-border-radius: 0; -boxpointer-gap: 0;');
                    self._pinBoxPointer(a, this);
                    break;
                }
            }
        });
        this._reloadMenus();
    }

    // As in XP: the menu opens against the left of the screen, with its bottom
    // at the top of the taskbar. BoxPointer's calculation centres it on the
    // button and the Zorin theme adds margins; here the position is computed
    // directly, with the inner offsets (top band on the left, bottom band at
    // the bottom) measured after each layout. No translations: the opening
    // animation resets them to 0 and the menu would jump.
    _pinBoxPointer(bp, layout) {
        if (bp._zxpPinned)
            return;
        bp._zxpPinned = true;
        // inner offsets already measured with the Zorin theme (they keep the first
        // opening from showing misaligned for an instant); confirmed afterwards
        bp._zxpOx = 0;   // from the BoxPointer's left to the top band's left
        bp._zxpOb = 5;   // from the bottom band's bottom to the BoxPointer's bottom (the shadow)
        bp.translation_x = 0;
        bp.translation_y = 0;
        bp._reposition = function (box) {
            const src = this._sourceActor;
            const monitor = Main.layoutManager.findIndexForActor(src);
            const work = Main.layoutManager.getWorkAreaForMonitor(monitor);
            const [, srcY] = src.get_transformed_position();
            const stageX = work.x - this._zxpOx;
            const stageY = srcY - box.get_height() + this._zxpOb;
            this.setArrowOrigin(0);
            let parent = this.get_parent();
            let ok = false, x = 0, y = 0;
            while (!ok && parent) {
                [ok, x, y] = parent.transform_stage_point(stageX, stageY);
                parent = parent.get_parent();
            }
            box.set_origin(Math.floor(x), Math.floor(y));
            debug(`posição: ${Math.floor(x)},${Math.floor(y)} altura=${box.get_height()} barra=${srcY} ` +
                `ox=${this._zxpOx} ob=${this._zxpOb} trans=${this.translation_x},${this.translation_y}`);
        };
        // measure the inner offsets and restore the position if they change
        const measure = () => {
            bp._zxpIdle = 0;
            if (!bp.visible || !layout._zxpHeader?.get_stage() || !layout._zxpFooter)
                return GLib.SOURCE_REMOVE;
            const [bx, by] = bp.get_transformed_position();
            const [hx] = layout._zxpHeader.get_transformed_position();
            const [, fy] = layout._zxpFooter.get_transformed_position();
            const ox = Math.round(hx - bx);
            const ob = Math.round((by + bp.height) - (fy + layout._zxpFooter.height));
            debug(`medida: ox=${ox} ob=${ob} bp=${bx},${by} ${bp.width}x${bp.height} layout=${layout.height}`);
            if (ox !== bp._zxpOx || ob !== bp._zxpOb) {
                bp._zxpOx = ox;
                bp._zxpOb = ob;
                bp.queue_relayout();
            }
            return GLib.SOURCE_REMOVE;
        };
        const queue = () => {
            if (!bp._zxpIdle)
                bp._zxpIdle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, measure);
        };
        bp.connectObject('notify::allocation', queue, 'notify::visible', queue, layout);
        layout.connectObject('destroy', () => {
            if (bp._zxpIdle)
                GLib.source_remove(bp._zxpIdle);
            bp._zxpIdle = 0;
            delete bp._reposition;
            bp._zxpPinned = false;
        }, layout);
        bp.queue_relayout();
    }

    _patch(proto, name, wrapper) {
        const orig = proto[name];
        if (typeof orig !== 'function')
            return;
        proto[name] = function (...args) {
            return wrapper.call(this, orig, ...args);
        };
        this._patches.push([proto, name, orig]);
    }

    // Rebuilds the menus already created with the current layout (patch on or not)
    _reloadMenus() {
        const panels = global.zorinTaskbar?.panels?.map(p => p?.panel) ?? [Main.panel];
        for (const panel of panels) {
            const button = panel?.statusArea?.['zorin-menu'];
            button?.menu?._reloadLayout?.();
        }
    }

    _xpify(layout) {
        if (layout._zxp)
            return;
        const left = layout._leftBox;
        const sep = layout._verticalSeparator?.actor;
        const sidebar = layout._sidebar;
        if (!left || !sidebar)
            return;
        layout._zxp = true;

        // Corpo: as duas colunas lado a lado
        const body = layout._zxpBody = new St.BoxLayout({
            style_class: 'zxp-start-body',
            x_expand: true,
            y_expand: true,
        });
        for (const a of [left, sep, sidebar]) {
            if (a && a.get_parent() === layout)
                layout.remove_child(a);
        }
        body.add_child(left);
        body.add_child(sidebar);
        sep?.destroy();
        left.add_style_class_name('zxp-start-left');
        sidebar.add_style_class_name('zxp-start-right');
        // inline measurements: zorin-menu's sheet is loaded after the theme and wins over it
        left.set_style(`padding: ${LEFT_PAD_T}px 4px ${LEFT_PAD_B}px 6px;`);
        sidebar.set_style('padding: 9px 8px 5px 6px;');
        left.set_width(LEFT_W);      // fixed width (CSS only gives the preferred one)
        const catBox = layout._categoriesSection?._categoriesBox;
        if (catBox) {
            for (const c of catBox.get_children())
                c._arrowIcon?.hide();
            catBox.connectObject('child-added', (_b, c) => c._arrowIcon?.hide(), layout);
        }
        const catScroll = layout._categoriesSection?._scrollBox;
        if (catScroll) {
            // no scroll: the category list measures and shows all its content
            catScroll.vscrollbar_policy = St.PolicyType.NEVER;
            catScroll.remove_style_class_name('vfade');
        }
        sidebar.set_width(RIGHT_W);

        layout.vertical = true;
        layout.add_style_class_name('zxp-start');
        layout.add_child(layout._zxpHeader = this._header(sidebar));
        // XP's shadow (drawn by win32k, it does not come in the theme; measured in
        // a real capture): 5 px of padding on the right and at the bottom, with
        // the background image generated in updateHeight. It stays inside the
        // menu's box: the BoxPointer is painted in its own buffer and whatever
        // leaves the box is lost
        layout.set_style(`padding: 0 ${SHADOW_W}px ${SHADOW_W}px 0;`);
        layout.add_child(body);
        layout.add_child(layout._zxpFooter = this._footerBox = this._footer(layout));

        // The user and the session buttons move to the bands. Zorin's
        // updateHeight shows the user again to measure the height: hide it
        // again after each call.
        const kids = sidebar.get_children();
        const sessionSep = kids[kids.indexOf(sidebar._sessionButtonsSection) - 1];
        const hideMoved = () => {
            sidebar._userItem?.hide();
            sidebar._userSeparator?.hide();
            sidebar._sessionButtonsSection?.hide();
            sessionSep?.hide();
        };
        hideMoved();
        const origUpdate = sidebar.updateHeight.bind(sidebar);
        sidebar.updateHeight = available => {
            origUpdate(available);
            hideMoved();
            // Fixed height, as in XP: the categories view's (all of them, no scroll),
            // whatever the current view — when a category opens or a search
            // runs, the longer lists scroll inside the column and the menu
            // does not jump
            const cats = layout._categoriesSection?._categoriesBox;
            const all = layout._allAppsButton;
            let natLeft = LEFT_PAD_T + LEFT_PAD_B;
            if (cats)
                natLeft += cats.get_preferred_height(LEFT_W)[1];
            if (all)
                natLeft += all.get_preferred_height(LEFT_W)[1] + LEFT_SEP_H;
            const [, natRight] = sidebar.get_preferred_height(RIGHT_W);
            return Math.min(available, Math.max(natRight, natLeft));
        };

        this._xpPlaces(sidebar);
        this._xpShortcuts(sidebar);
        // Right column with XP's measurements (Screenshot_20261011171012):
        // 26 px items (icon 1 px from the top and 2 px from the left, text 4 px
        // after the icon) with 4 px between them; 12 px separators with the
        // line (StartPanel.PlacesListSeparator, 134×2, real size) 7 px below
        // the previous item and at x=28. The leftover space stays at the
        // bottom, as in XP. All inline: zorin-menu's sheet wins over the theme
        // on these selectors
        const xpRight = a => {
            if (a.has_style_class_name?.('popup-separator-menu-item')) {
                a.set_style('padding: 3px 0 3px 0; margin: 0; min-height: 0; spacing: 0;');
                const line = a._separator ??
                    a.get_children().find(c => c.has_style_class_name?.('popup-separator-menu-item-separator'));
                if (line) {
                    line.x_expand = false;
                    line.x_align = Clutter.ActorAlign.START;
                    line.set_width(134);
                    line.set_style('height: 2px; margin: 0 0 0 22px; padding: 0; background-size: 134px 2px;');
                }
                return;
            }
            if (a.has_style_class_name?.('popup-menu-item')) {
                a.y_expand = false;
                a.set_style('padding: 1px 4px 1px 2px; spacing: 4px; margin: 0 0 4px 0;');
                return;
            }
            if (a !== sidebar && a instanceof St.BoxLayout) {
                a.y_expand = false;
                a.set_style('padding: 0; margin: 0; spacing: 0;');
            }
            for (const c of a.get_children())
                xpRight(c);
        };
        xpRight(sidebar);

        this._xpMorePrograms(layout, left);
        this._xpScrollBars(layout);

        // Zorin's search in the bottom band, on the left (as in the mock-up)
        const search = layout._searchEntry;
        if (search) {
            search.get_parent()?.remove_child(search);
            search.add_style_class_name('zxp-start-search');
            search.set_style('margin: 0; border-radius: 3px;');
            search.set_position(SEARCH_X, Math.floor((FOOTER_H - SEARCH_H) / 2));
            search.set_size(SEARCH_W, SEARCH_H);
            this._footerBox.add_child(search);
            // Always hidden (XP's bottom band only has Log Off and Turn Off), but
            // working: with the menu open, any key starts the search in Zorin
            // and the results appear on the left
            search.opacity = 0;
            search.reactive = false;
        }
    }

    // "Todos os programas" as in XP: separator above, bold text (#373738)
    // right-aligned and the green arrow (StartPanel.MoreProgramsArrow / hot)
    // 8 px from the edge; the highlight takes 175×24, from x=7 to the arrow.
    // "Voltar" is the mirror: same height, font and highlight, arrow to the left
    _xpMorePrograms(layout, left) {
        // XP separator above "Todos os programas" and "Voltar"
        // (each one only visible when its button is visible)
        for (const btn of [layout._allAppsButton, layout._backButton]) {
            if (!btn)
                continue;
            const sep = this._xpLeftSeparator(XP_DIR);
            left.insert_child_below(sep, btn);
            btn.bind_property('visible', sep, 'visible', GObject.BindingFlags.SYNC_CREATE);
        }
        // "Todos os programas" with a lowercase p, as in XP (Zorin writes "Programas")
        this._xpGreenButton(layout._allAppsButton, 'Todos os programas', 'start-more-arrow', false);
        this._xpGreenButton(layout._backButton, 'Voltar', 'start-back-arrow', true);
    }

    _xpGreenButton(btn, text, arrowName, arrowFirst) {
        if (!btn)
            return;
        btn.add_style_class_name('zxp-more-programs');
        // inline: zorin-menu's sheet wins over the theme in the items' padding
        btn.set_style('padding: 0; margin: 0 4px 0 1px; spacing: 12px; min-height: 24px; border-radius: 0;');
        btn._icon?.hide();
        const label = btn.get_children().find(c => c instanceof St.Label);
        if (label) {
            label.text = text;
            label.x_expand = true;
            label.x_align = arrowFirst ? Clutter.ActorAlign.START : Clutter.ActorAlign.END;
            label.y_align = Clutter.ActorAlign.CENTER;
        }
        // seta no tamanho original (16×24): um St.Icon quadrado deformava-a
        const arrowStyle = h => `background-image: url("file://${XP_DIR}/${arrowName}${h ? '-hot' : ''}.png"); ` +
            'background-size: 16px 24px; background-repeat: no-repeat;';
        const arrow = new St.Widget({
            width: 16,
            height: 24,
            y_align: Clutter.ActorAlign.CENTER,
            style: arrowStyle(false),
        });
        if (arrowFirst)
            btn.insert_child_at_index(arrow, 0);
        else
            btn.add_child(arrow);
        // "hot" arrow with the highlight: mouse over or item chosen with the keyboard
        const hot = () => {
            const style = arrowStyle(btn.hover || btn.has_style_class_name('selected'));
            if (arrow.style !== style)
                arrow.style = style;
        };
        btn.connectObject('notify::hover', hot, 'style-changed', hot, arrow);
    }

    // XP scrollbars in the left column lists: they take 17 px (they do not
    // sit on top of the list, no fading) and the arrows, which the theme draws
    // in the border-image, work as in Windows: one click moves one line and,
    // holding it pressed, repeats
    _xpScrollBars(layout) {
        const walk = a => {
            if (a instanceof St.ScrollView)
                this._xpScrollBar(a, layout);
            for (const c of a.get_children())
                walk(c);
        };
        walk(layout);
    }

    _xpScrollBar(view, layout) {
        const bar = view.get_vscroll_bar?.() ?? view.vscroll;
        if (!bar || bar._zxp)
            return;
        bar._zxp = true;
        view.overlay_scrollbars = false;
        view.remove_style_class_name('vfade');
        bar.z_position = 0;
        bar.reactive = true;
        const handle = bar.get_children().find(c => c.name === 'vhandle');
        let zone = null, pressed = null, timer = 0, grab = null;

        // Bar (arrows + trough) and thumb (with the grip centred, if it fits)
        // as images of the exact size, swapped according to the state
        const paint = () => {
            const h = Math.round(bar.height);
            if (h >= 2 * ARROW_H) {
                let state = 'normal';
                if (pressed && zone === pressed)
                    state = `${pressed}-active`;
                else if (!pressed && zone)
                    state = `${zone}-hover`;
                const img = slicedImage(`scroll-vbar-${state}`, 17, h, [ARROW_H, 0, ARROW_H, 0]);
                const style = `background-image: url("file://${img}"); background-position: 0 0;`;
                if (bar.get_style() !== style)
                    bar.set_style(style);
            }
            const th = Math.round(handle?.height ?? 0);
            if (handle && th >= 10) {
                const state = handle.has_style_pseudo_class('active') ? 'active'
                    : handle.hover ? 'hover' : 'normal';
                // the grip only shows if it fits within the thumb's margins (4 + 8 + 4)
                const img = slicedImage(`scroll-thumb-${state}`, 17, th, [5, 5, 5, 5],
                    th >= 16 ? `scroll-grip-${state}` : null);
                const style = `background-image: url("file://${img}"); background-position: 0 0;`;
                if (handle.get_style() !== style)
                    handle.set_style(style);
            }
        };
        const zoneAt = event => {
            const [sx, sy] = event.get_coords();
            const [ok, x, y] = bar.transform_stage_point(sx, sy);
            if (!ok || x < 0 || x >= bar.width)
                return null;
            if (y >= 0 && y < ARROW_H)
                return 'up';
            if (y >= bar.height - ARROW_H && y < bar.height)
                return 'down';
            return null;
        };
        // one line = the height of a list item
        const line = () => {
            const find = a => {
                if (a.visible && a.has_style_class_name?.('popup-menu-item') && a.height > 0)
                    return a.height;
                for (const c of a.get_children()) {
                    const h = find(c);
                    if (h)
                        return h;
                }
                return 0;
            };
            return find(view) || bar.adjustment.step_increment;
        };
        // only moves with the button pressed over the arrow where it was pressed
        const step = () => {
            if (!pressed || zone !== pressed)
                return;
            const adj = bar.adjustment;
            const v = adj.value + (pressed === 'up' ? -line() : line());
            adj.value = Math.max(adj.lower, Math.min(adj.upper - adj.page_size, v));
        };
        const stop = () => {
            if (timer)
                GLib.source_remove(timer);
            timer = 0;
            grab?.dismiss();
            grab = null;
            pressed = null;
            for (const a of view.get_actions())
                a.enabled = true;
            paint();
        };
        bar.connectObject(
            'motion-event', (_a, event) => {
                zone = zoneAt(event);
                paint();
                return Clutter.EVENT_PROPAGATE;
            },
            'leave-event', () => {
                if (!pressed) {
                    zone = null;
                    paint();
                }
                return Clutter.EVENT_PROPAGATE;
            },
            'button-press-event', (_a, event) => {
                if (event.get_button() !== Clutter.BUTTON_PRIMARY || pressed)
                    return Clutter.EVENT_PROPAGATE;
                zone = zoneAt(event);
                if (!zone)
                    return Clutter.EVENT_PROPAGATE;
                pressed = zone;
                // grabs the mouse until the button is released (even outside the bar),
                // as St does when dragging the thumb; the gesture of dragging the
                // list (Zorin's PanAction) is off in the meantime
                const focus = global.stage.key_focus;
                if (focus && focus !== layout && layout.contains(focus))
                    global.stage.set_key_focus(layout);
                grab = global.stage.grab(bar);
                for (const a of view.get_actions())
                    a.enabled = false;
                paint();
                step();
                // repetition: the first after ~1/3 s, then every 50 ms
                timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 330, () => {
                    timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                        step();
                        return GLib.SOURCE_CONTINUE;
                    });
                    step();
                    return GLib.SOURCE_REMOVE;
                });
                return Clutter.EVENT_STOP;
            },
            'button-release-event', () => {
                if (!pressed)
                    return Clutter.EVENT_PROPAGATE;
                stop();
                return Clutter.EVENT_STOP;
            },
            'notify::height', paint,
            layout);
        handle?.connectObject('notify::height', paint, 'notify::hover', paint,
            'style-changed', paint, layout);
        layout.connectObject('destroy', stop, bar);
        view.connectObject('notify::mapped', () => {
            if (!view.mapped)
                stop();
        }, layout);
        paint();
    }

    // XP separator (StartPanel.ProgListSeparator, 172×2) with the image at x=12
    // (the visible part goes from 18 to 177, as in the capture), 10 px in total
    _xpLeftSeparator(xp) {
        const line = new St.Widget({
            width: 172,
            height: 2,
            x_expand: true,
            x_align: Clutter.ActorAlign.START,
            style: `background-image: url("file://${xp}/start-sep-left.png"); ` +
                'background-size: 172px 2px; background-repeat: no-repeat;',
        });
        return new St.Bin({
            child: line,
            x_expand: true,
            style: 'padding: 3px 0 5px 6px;',
        });
    }

    _icon(key) {
        const path = `${XP_DIR}/start-ico-${key}.png`;
        return Gio.FileIcon.new(Gio.File.new_for_path(path));
    }

    // Places as in XP, in the order chosen by the user and with XP's 24 px
    // icons; the others (Transferências, etc.) are hidden.
    // "O meu computador" opens the home folder.
    _xpPlaces(sidebar) {
        const places = sidebar._placesSection;
        const items = places?._items;
        if (!items)
            return;
        places.add_style_class_name('zxp-places');
        const dir = d => GLib.get_user_special_dir(d);
        const U = GLib.UserDirectory;
        const order = [
            [dir(U.DIRECTORY_DOCUMENTS), 'Os meus documentos', 'documents'],
            [dir(U.DIRECTORY_DESKTOP), 'Ambiente de trabalho', 'desktop'],
            [dir(U.DIRECTORY_PICTURES), 'As minhas imagens', 'pictures'],
            [dir(U.DIRECTORY_MUSIC), 'A minha música', 'music'],
            [GLib.get_home_dir(), 'O meu computador', 'computer'],
        ];
        const byPath = new Map(items.map(it => [it._info?.file?.get_path?.(), it]));
        for (const it of items)
            places.remove_child(it);
        const shown = new Set();
        for (const [path, label, key] of order) {
            const it = byPath.get(path);
            if (!it || shown.has(it))
                continue;
            shown.add(it);
            places.add_child(it);
            const apply = () => {
                it._label.text = label;
                it._icon.gicon = this._icon(key);
                it._icon.icon_size = 24;
            };
            // Zorin updates the name/icon asynchronously: apply again afterwards
            it._info.connectObject('changed', apply, it);
            apply();
        }
        for (const it of items) {
            if (!shown.has(it)) {
                places.add_child(it);
                it.hide();
            }
        }
    }

    // Shortcuts with XP icons (chosen by the user) and, after a second
    // separator, Internet (XP globe, default browser), Downloads and the
    // Terminal with the Command Prompt icon (cmd.exe)
    _xpShortcuts(sidebar) {
        const shortcuts = sidebar._shortcutsSection;
        if (shortcuts && this._misc?.ShortcutMenuItem) {
            const closeMenu = item => {
                let a = item;
                while (a && !a._delegate?.close)
                    a = a.get_parent();
                a?._delegate?.close();
            };
            const add = (label, command, key) => {
                const it = new this._misc.ShortcutMenuItem(label, command, 'application-x-executable-symbolic');
                it._icon.gicon = this._icon(key);
                it._icon.icon_size = 24;
                it.connect('activated', () => closeMenu(it));
                shortcuts.add_child(it);
                return it;
            };
            shortcuts.add_child(new PopupMenu.PopupSeparatorMenuItem());
            // Internet: o navegador predefinido (lido no momento do clique)
            const net = add('Internet', ['true'], 'internet');
            net.activate = event => {
                const app = Gio.AppInfo.get_default_for_uri_scheme('https');
                app?.launch([], global.create_app_launch_context(event?.get_time?.() ?? 0, -1));
                net.emit('activated');
            };
            // Downloads: the downloads folder (read at click time: it may have moved
            // after the menu was built)
            const downloads = add('Downloads', ['true'], 'downloads');
            downloads.activate = event => {
                GLib.reload_user_special_dirs_cache();
                const path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) ??
                    GLib.get_home_dir();
                try {
                    Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(path).get_uri(),
                        global.create_app_launch_context(event?.get_time?.() ?? 0, -1));
                } catch (e) {
                    console.warn(`Zorin XP: Downloads: ${e.message}`);
                }
                downloads.emit('activated');
            };
            add('Terminal', ['x-terminal-emulator'], 'terminal');
        }
        const icons = {
            'gnome-software': 'programs',
            'gnome-control-center': 'settings',
            'zorin-appearance': 'appearance',
        };
        const walk = a => {
            const key = icons[a._command?.[0]];
            if (key && a._icon) {
                a._icon.gicon = this._icon(key);
                a._icon.icon_size = 24;
            }
            for (const c of a.get_children())
                walk(c);
        };
        walk(sidebar);
    }

    _header() {
        const header = new St.Widget({style_class: 'zxp-start-header', x_expand: true, height: HEADER_H,
            layout_manager: new Clutter.FixedLayout()});
        const tile = new St.Bin({style_class: 'zxp-start-usertile', x: 1, y: 1});
        const user = AccountsService.UserManager.get_default().get_user(GLib.get_user_name());
        const pic = new St.Bin({style_class: 'zxp-start-userpic', width: 48, height: 48});
        tile.set_child(pic);
        const name = new St.Label({style_class: 'zxp-start-username', x: 67, y: 20});
        const sync = () => {
            const file = user.get_icon_file?.();
            if (file && GLib.file_test(file, GLib.FileTest.EXISTS)) {
                pic.set_child(null);
                pic.style = `background-image: url("file://${file}"); background-size: 48px 48px;`;
            } else {
                pic.style = 'background-color: #ffffff;';
                pic.set_child(new St.Icon({icon_name: 'avatar-default-symbolic', icon_size: 40,
                    style_class: 'zxp-start-noavatar'}));
            }
            name.text = user.get_real_name() || user.get_user_name() || GLib.get_user_name();
        };
        user.connectObject('changed', sync, header);
        if (user.is_loaded)
            sync();
        else
            user.connectObject('notify::is-loaded', sync, header);
        header.add_child(tile);
        header.add_child(name);
        return header;
    }

    _footer(layout) {
        const footer = new St.Widget({style_class: 'zxp-start-footer', x_expand: true, height: FOOTER_H,
            layout_manager: new Clutter.FixedLayout()});
        const actions = SystemActions.getDefault();
        // as in XP: Start closes first (at once, without animation) and only then
        // does the turn off/log off dialog appear
        const close = () => closeStartMenus();
        const mk = (x, icon, text, fn) => {
            const b = new St.Button({style_class: 'zxp-start-session', x, y: 8, can_focus: true,
                track_hover: true});
            const box = new St.BoxLayout({style_class: 'zxp-start-session-box'});
            const ic = new St.Bin({style_class: `zxp-start-session-icon zxp-${icon}`, width: 24, height: 24});
            box.add_child(ic);
            box.add_child(new St.Label({text, y_align: Clutter.ActorAlign.CENTER}));
            b.set_child(box);
            b.connect('clicked', () => {
                close();
                fn();
            });
            return b;
        };
        // XP's dialog opens right after Start closes (without going through
        // gnome-session); without the end-session extension, GNOME's ones

        footer.add_child(mk(LOGOFF_X, 'logoff', 'Terminar sessão',
            () => showEndSession(LOGOUT) || actions.activateLogout()));
        footer.add_child(mk(SHUTDOWN_X, 'shutdown', 'Encerrar',
            () => showEndSession(SHUTDOWN) || actions.activatePowerOff()));
        return footer;
    }

    destroy() {
        this._destroyed = true;
        for (const [proto, name, orig] of this._patches.reverse())
            proto[name] = orig;
        this._patches = [];
        this._reloadMenus();
    }
}
