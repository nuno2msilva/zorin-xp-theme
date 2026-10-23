/*
 * On the taskbar, each Explorer (Files) window with the icon of the folder it
 * has open, as in XP — zorin-taskbar gives them all the application's icon
 * (the "O meu computador" one).
 *
 * Each window's folder comes from Nautilus itself
 * (org.freedesktop.FileManager1, OpenWindowsWithLocations property: the
 * window's D-Bus path -> locations) and each window's D-Bus path comes from
 * mutter. The icon is the folder's (the same as the Explorer's title and
 * address bar): the one chosen for the place (shortcut-icons.json, the
 * Shortcuts' one) or, at the root of a mounted disk, XP's disk icon — like
 * the Explorer's placeIcon (src/nautilus-xp: _place_icon).
 */
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

const FILES = ['org.gnome.Nautilus', 'Org.gnome.Nautilus', 'nautilus'];
const PLACE_ICONS = GLib.build_filenamev([GLib.get_user_data_dir(), 'zorin-xp', 'shortcut-icons.json']);
const NETWORK_FS = ['cifs', 'smb3', 'smbfs', 'nfs', 'nfs4', 'fuse.sshfs', 'sshfs', '9p', 'vboxsf', 'davfs'];
// Recent and Favorites: XP's colour icons, as in the Explorer's sidebar
const SCHEME_ICONS = {recent: 'folder-recent', starred: 'user-bookmarks'};
const BUS_NAME = 'org.freedesktop.FileManager1';
const BUS_PATH = '/org/freedesktop/FileManager1';

// a button's own icon on the taskbar (zorin-taskbar gives them all the
// application's): swaps the createIcon of the button's icon. Also used by
// zenIcons.js. Returns true if it changed.
export function setButtonIcon(button, gicon) {
    const base = button.icon;
    if (!base || (button._zxpGicon && button._zxpGicon.equal(gicon)))
        return false;
    if (!button._zxpCreateIcon)
        button._zxpCreateIcon = base.createIcon;
    button._zxpGicon = gicon;
    base.createIcon = size => new St.Icon({gicon, icon_size: size});
    refreshIcon(base);
    return true;
}

export function restoreButtonIcon(button) {
    if (button.icon && button._zxpCreateIcon) {
        button.icon.createIcon = button._zxpCreateIcon;
        refreshIcon(button.icon);
    }
    delete button._zxpCreateIcon;
    delete button._zxpGicon;
}

function refreshIcon(base) {
    if (typeof base.update === 'function')
        base.update();
    else
        base._createIconTexture?.(base.iconSize);
}

// the zorin-taskbar buttons (one per window)
export function taskbarButtons() {
    const out = [];
    for (const panel of global.zorinTaskbar?.panels ?? []) {
        for (const c of panel?.taskbar?._getTaskbarIcons?.() ?? []) {
            const button = c.child?._delegate;
            if (button?.window)
                out.push(button);
        }
    }
    return out;
}

export class ExplorerIcons {
    constructor() {
        this._locations = {};          // window D-Bus path -> uri
        this._icons = new Map();       // uri -> GIcon
        this._buttons = new Set();     // buttons with a changed icon
        this._timer = 0;
        // (without starting Nautilus just for this)
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START, null,
            BUS_NAME, BUS_PATH, BUS_NAME, null, (_o, res) => {
                try {
                    this._proxy = Gio.DBusProxy.new_for_bus_finish(res);
                } catch (e) {
                    console.warn(`Zorin XP: ícones das pastas na barra: ${e.message}`);
                    return;
                }
                if (this._destroyed)
                    return;
                this._proxy.connectObject(
                    'g-properties-changed', () => this._load(),
                    'notify::g-name-owner', () => this._load(), this);
                this._load();
            });
        // (a new window's button appears shortly after the window)
        global.display.connectObject('window-created', () => this._soon(), this);
    }

    _soon() {
        if (this._timer)
            return;
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 400, () => {
            this._timer = 0;
            this._update();
            return GLib.SOURCE_REMOVE;
        });
    }

    _load() {
        this._locations = {};
        const value = this._proxy?.get_cached_property('OpenWindowsWithLocations');
        for (const [path, uris] of Object.entries(value?.deepUnpack() ?? {})) {
            if (uris.length)
                this._locations[path] = uris[0];
        }
        this._update();
    }

    _update() {
        for (const button of taskbarButtons()) {
            const win = button.window;
            if (!FILES.includes(win.get_wm_class()))
                continue;
            const uri = this._locations[win.get_gtk_window_object_path?.()];
            if (uri)
                this._iconFor(uri, gicon => this._setIcon(button, gicon));
        }
    }

    _iconFor(uri, done) {
        const cached = this._icons.get(uri);
        if (cached) {
            done(cached);
            return;
        }
        const keep = gicon => {
            if (this._destroyed || !gicon)
                return;
            this._icons.set(uri, gicon);
            done(gicon);
        };
        const special = SCHEME_ICONS[Gio.File.new_for_uri(uri).get_uri_scheme()];
        if (special) {
            keep(new Gio.ThemedIcon({name: special}));
            return;
        }
        const chosen = this._chosenIcon(uri);
        if (chosen) {
            keep(chosen);
            return;
        }
        const file = Gio.File.new_for_uri(uri);
        file.query_info_async('standard::icon,unix::device', Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_DEFAULT, null, (_f, res) => {
                let info;
                try {
                    info = file.query_info_finish(res);
                } catch (e) {
                    return;
                }
                const parent = file.get_path() ? file.get_parent() : null;
                if (!parent || !info.has_attribute('unix::device')) {
                    keep(info.get_icon());
                    return;
                }
                // the root of a mounted disk: on a different device than the folder above
                parent.query_info_async('unix::device', Gio.FileQueryInfoFlags.NONE,
                    GLib.PRIORITY_DEFAULT, null, (_p, res2) => {
                        let up;
                        try {
                            up = parent.query_info_finish(res2);
                        } catch (e) {
                            keep(info.get_icon());
                            return;
                        }
                        if (up.get_attribute_uint32('unix::device') === info.get_attribute_uint32('unix::device')) {
                            keep(info.get_icon());
                            return;
                        }
                        file.query_filesystem_info_async('filesystem::type', GLib.PRIORITY_DEFAULT, null,
                            (_q, res3) => {
                                let fs = '';
                                try {
                                    fs = file.query_filesystem_info_finish(res3).get_attribute_string('filesystem::type') ?? '';
                                } catch (e) {}
                                keep(new Gio.ThemedIcon({name: NETWORK_FS.includes(fs) ? 'folder-remote' : 'drive-harddisk'}));
                            });
                    });
            });
    }

    _chosenIcon(uri) {
        // (the Shortcuts file: address -> icon; small, read every time)
        try {
            const [, data] = GLib.file_get_contents(PLACE_ICONS);
            const map = JSON.parse(new TextDecoder().decode(data));
            const name = map[uri] ?? map[Gio.File.new_for_uri(uri).get_uri()];
            return name ? new Gio.ThemedIcon({name}) : null;
        } catch (e) {
            return null;
        }
    }

    _setIcon(button, gicon) {
        if (setButtonIcon(button, gicon))
            this._buttons.add(button);
    }

    destroy() {
        this._destroyed = true;
        if (this._timer)
            GLib.source_remove(this._timer);
        global.display.disconnectObject(this);
        this._proxy?.disconnectObject(this);
        this._proxy = null;
        for (const button of this._buttons)
            restoreButtonIcon(button);
        this._buttons.clear();
        this._icons.clear();
    }
}
