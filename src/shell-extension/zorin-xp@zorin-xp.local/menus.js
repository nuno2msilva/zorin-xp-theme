/*
 * The Shell's context menus (taskbar, notification area icons, application
 * menus) with the look of XP's menus: square white box, #ACA899 outline,
 * #316AC5 highlight, 17 px items.
 *
 * The CSS only reaches menus marked with .zxp-menu: the GNOME panels that
 * are also PopupMenus (quick settings, calendar, Start menu) have their own
 * look and stay out.
 */
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const SKIP_MENUS = ['QuickSettingsMenu'];
const SKIP_SOURCES = ['DateMenuButton', 'QuickSettings'];

function isXpMenu(menu) {
    if (SKIP_MENUS.includes(menu.constructor.name))
        return false;
    if (SKIP_SOURCES.includes(menu.sourceActor?.constructor?.name))
        return false;
    return !menu.actor.has_style_class_name('zorin-menu');
}

// items with a mark (check, dot): the mark takes the 17 px column to the
// left of the text, as in XP
function markOrnaments(menu) {
    for (const item of menu._getMenuItems()) {
        if (item instanceof PopupMenu.PopupMenuSection)
            markOrnaments(item);
        else if (item._ornamentIcon)
            item[item._ornamentIcon.visible ? 'add_style_class_name' : 'remove_style_class_name']('zxp-ornamented');
    }
}

// section titles (separators with text): XP's menus did not have them, and
// in the 7 px separator the text was cut by the line. The "Janelas
// abertas" (Open Windows) of the application menu (taskbar) goes away
// entirely — only the window list stays, separated from the rest; in the
// other menus only the line stays.
function dropHeadings(menu, touched) {
    const header = menu._openWindowsHeader;
    for (const item of menu._getMenuItems()) {
        if (item instanceof PopupMenu.PopupMenuSection) {
            dropHeadings(item, touched);
        } else if (item instanceof PopupMenu.PopupSeparatorMenuItem && item.label.text && !touched.has(item)) {
            touched.set(item, item.connect('destroy', () => touched.delete(item)));
            item.label.visible = false;
            if (item === header) {
                // (GNOME shows and hides it with the windows: it gets no height)
                item._separator.visible = false;
                item.add_style_class_name('zxp-gone');
            }
        }
    }
}

export class MenuTweaks {
    constructor() {
        const proto = PopupMenu.PopupMenu.prototype;
        this._origOpen = proto.open;
        const origOpen = this._origOpen;
        const touched = this._touched = new Map();      // item -> sinal destroy
        proto.open = function (...args) {
            if (isXpMenu(this)) {
                this.actor.add_style_class_name('zxp-menu');
                markOrnaments(this);
                dropHeadings(this, touched);
            }
            return origOpen.apply(this, args);
        };
    }

    destroy() {
        PopupMenu.PopupMenu.prototype.open = this._origOpen;
        for (const [item, id] of this._touched) {
            item.disconnect(id);
            item.label.visible = item.label.text !== '';
            item._separator.visible = true;
            item.remove_style_class_name('zxp-gone');
        }
        this._touched.clear();
    }
}
