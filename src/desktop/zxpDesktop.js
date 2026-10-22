/* Zorin XP — o ambiente de trabalho como o do XP (zorin-desktop-icons).
 *
 * tools/setup/dingcopy.py põe este ficheiro na cópia do programa dos ícones e liga-o
 * em desktopManager.js:
 *  - doRename: o nome editado no sítio — caixa branca com moldura preta por
 *    cima da legenda (várias linhas ao centro se o nome não couber), em vez do
 *    balão do GNOME; Enter ou clicar fora confirma, Esc cancela; a pergunta do
 *    XP ao mudar a extensão e o erro do XP se o nome já existir;
 *  - doTrash / doDeletePermanently: a pergunta do XP (diálogos 1011-1013 do
 *    shell32) com o ícone da Reciclagem e, ao mandar para lá, o som dela;
 *  - o menu do fundo do XP: Dispor ícones por, Actualizar, Colar, Colar
 *    atalho, Anular, Novo > Pasta e modelos, Propriedades.
 * Os textos e ícones vêm do XP (dingcopy.py -> zxp/strings.json, zxp/msg-*.png).
 */
/* exported startRename, confirmDelete, xpMenu, prepareMenu */
'use strict';
const {Gtk, Gdk, Gio, GLib, GObject, Pango} = imports.gi;
const GioUnix = imports.gi.GioUnix;
const DBusUtils = imports.dbusUtils;
const DesktopIconsUtil = imports.desktopIconsUtil;
const Prefs = imports.preferences;
const Enums = imports.enums;

const DATA = '@DATA@';
const RECYCLE = GLib.build_filenamev([GLib.get_user_data_dir(), 'sounds', 'WindowsXP', 'xp',
    'Windows XP Recycle.wav']);
const LINE = 13;                        // Tahoma 8 no XP: linhas de 13 px
const DEFAULTS = {
    yes: '&Sim', no: '&Não', ok: 'OK', rename: '&Mudar o nome', newFolder: 'Nova pasta',
    confirmFile: 'Confirmar eliminação de ficheiro(s)', confirmFolder: 'Confirmar eliminação de pasta(s)',
    confirmMany: 'Confirmar eliminação de vários ficheiros',
    askFile: "Tem a certeza de que pretende mandar '%1' para a 'Reciclagem'?",
    askFolder: "Tem a certeza de que pretende remover a pasta '%1' e mover todo o conteúdo para a 'Reciclagem'?",
    askMany: "Tem a certeza de que pretende mandar estes %1 itens para a 'Reciclagem'?",
    killFile: "Tem a certeza de que pretende eliminar '%1'?",
    killFolder: "Tem a certeza de que pretende remover a pasta '%1' e %3", allContents: 'todo o seu conteúdo?',
    killMany: 'Tem a certeza de que pretende eliminar estes %1 itens?',
    askExtension: 'Se alterar uma extensão de nome de ficheiro, poderá não ser possível utilizar o ficheiro.\n\n' +
        'Tem a certeza de que pretende alterá-la?',
    badChars: 'Um nome de ficheiro não pode conter nenhum dos seguintes caracteres:\n\t \\ / :  * ? " < > | ',
    renameError: 'Erro ao mudar o nome a ficheiro ou pasta', renameFailed: 'Não é possível mudar o nome de %2: %1',
    nameExists: 'Já existe um ficheiro com o nome que especificou. Especifique um nome de ficheiro diferente.',
    arrange: '&Dispor ícones por', refresh: 'Actuali&zar', paste: '&Colar', pasteLink: 'Colar atal&ho',
    undo: 'An&ular', new: '&Novo', newFolderItem: '&Pasta', desktopProperties: 'Propriedade&s',
    colName: 'Nome', colSize: 'Tamanho', colType: 'Tipo', modified: 'Modificado',
    groups: 'Mostrar por &grupos', autoArrange: 'Dispor a&utomaticamente', alignGrid: 'Dispor em grel&ha',
    shortcutTo: 'Atalho para %1',
};

let _strings = null;
function t(key) {
    if (_strings === null) {
        _strings = {};
        try {
            const [ok, bytes] = GLib.file_get_contents(GLib.build_filenamev([DATA, 'strings.json']));
            if (ok)
                _strings = JSON.parse(new TextDecoder().decode(bytes));
        } catch (e) {
            console.log(`Zorin XP: ${e.message}`);
        }
    }
    return _strings[key] || DEFAULTS[key] || key;
}

function mnemonic(text) {
    return text.replace(/_/g, '__').replace(/&&/g, '\0').replace(/&/g, '_').replace(/\0/g, '&');
}

function plain(text) {
    return text.replace(/&&/g, '\0').replace(/&/g, '').replace(/\0/g, '&');
}

function fmt(text, ...args) {
    return text.replace(/%(\d)(?:![^!]*!)?/g, (m, n) => (args[n - 1] ?? '').toString());
}

let _css = null;
function ensureCss() {
    if (_css)
        return;
    _css = new Gtk.CssProvider();
    _css.load_from_data(new TextEncoder().encode(`
entry.zxp-rename { min-height: 0; padding: 0 5px; border: 1px solid #000; border-radius: 0; border-image: none;
  box-shadow: none; outline: none; background-color: #FFF; background-image: none; color: #000; text-shadow: none; }
entry.zxp-rename selection, textview.zxp-rename text selection { background-color: #316AC5; color: #FFF; }
frame.zxp-rename > border { border: 1px solid #000; border-radius: 0; border-image: none; box-shadow: none; }
frame.zxp-rename, textview.zxp-rename, textview.zxp-rename text { background-color: #FFF; color: #000; text-shadow: none; }
window.zxp-msgbox label.zxp-msgbox-text { color: #000; text-shadow: none; }
window.zxp-msgbox button { min-height: 0; min-width: 0; padding: 0; }
`));
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), _css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10);
}

function lineAttrs() {
    const attrs = new Pango.AttrList();
    attrs.insert(Pango.attr_line_height_new_absolute(LINE * Pango.SCALE));
    return attrs;
}

function eventSounds() {
    try {
        return new Gio.Settings({schema_id: 'org.gnome.desktop.sound'}).get_boolean('event-sounds');
    } catch (e) {
        return false;
    }
}

function playSound(file, event) {
    if (!eventSounds() || (file && !GLib.file_test(file, GLib.FileTest.EXISTS)))
        return;
    try {
        Gio.Subprocess.new(['canberra-gtk-play', ...(file ? ['-f', file] : ['-i', event])],
            Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE);
    } catch (e) {
        console.log(`Zorin XP: ${e.message}`);
    }
}

/* text em linhas de width px como o DrawText do XP (DT_WORDBREAK): parte nos
   espaços; lines = null -> o texto todo, as palavras compridas partidas */
function xpWrap(text, width, measure, lines = null) {
    if (measure(text) <= width)
        return text;
    const fits = s => {
        let lo = 1, hi = s.length;
        while (lo < hi) {
            const mid = (lo + hi + 1) >> 1;
            if (measure(s.slice(0, mid)) <= width)
                lo = mid;
            else
                hi = mid - 1;
        }
        return lo;
    };
    const cut = s => {
        if (measure(s) <= width)
            return s;
        let lo = 0, hi = s.length;
        while (lo < hi) {
            const mid = (lo + hi + 1) >> 1;
            if (measure(`${s.slice(0, mid).trimEnd()}...`) <= width)
                lo = mid;
            else
                hi = mid - 1;
        }
        return `${s.slice(0, lo).trimEnd()}...`;
    };
    const out = [];
    let rest = text;
    while (rest && (lines === null || out.length < lines)) {
        if (lines !== null && out.length === lines - 1) {
            out.push(cut(rest));
            break;
        }
        const words = rest.split(' ');
        let line = words[0];
        if (measure(line) > width) {
            if (lines === null) {
                const n = fits(line);
                out.push(line.slice(0, n));
                rest = rest.slice(n);
                continue;
            }
            out.push(cut(line));
            break;
        }
        let i = 1;
        while (i < words.length && measure(`${line} ${words[i]}`) <= width)
            line += ` ${words[i++]}`;
        out.push(line);
        rest = words.slice(i).join(' ');
    }
    return out.join('\n');
}

/* ------------------------------------------------------------ caixas do XP */

/* Uma caixa do XP; callback(índice do botão). shell: a confirmação de
   eliminar do shell32 (412 x 127, vários itens 412 x 97, ícone em (15, 15),
   Sim / Não em baixo à direita); senão uma MessageBox do user32 (margem de
   11 px, texto a 62 px, botões de 75 x 23 ao centro, 17 px abaixo). */
function messageBox({title, text, icon, buttons = ['ok'], def = 0, escape = null, shell = false, many = false},
    callback) {
    ensureCss();
    const win = new Gtk.Window({title, type_hint: Gdk.WindowTypeHint.DIALOG, resizable: false,
        window_position: Gtk.WindowPosition.CENTER});
    win.get_style_context().add_class('zxp-msgbox');
    win.set_keep_above(true);
    const fixed = new Gtk.Fixed();
    const label = new Gtk.Label({xalign: 0, yalign: 0});
    label.get_style_context().add_class('zxp-msgbox-text');
    label.set_attributes(lineAttrs());
    const measure = s => label.create_pango_layout(s).get_pixel_size()[0];
    const img = Gtk.Image.new_from_file(GLib.build_filenamev([DATA, `msg-${icon}.png`]));
    const btns = buttons.map(key => Gtk.Button.new_with_mnemonic(mnemonic(t(key))));
    if (shell) {
        fixed.set_size_request(412, many ? 97 : 127);
        fixed.put(img, 15, 15);
        const width = many ? 336 : 330;
        label.set_text(text.split('\n').map(p => p ? xpWrap(p, width, measure) : '').join('\n'));
        fixed.put(label, many ? 62 : 57, many ? 21 : 15);
        const pos = many ? [220, 315] : [236, 322];
        btns.forEach((b, i) => {
            b.set_size_request(many ? 87 : 80, 23);
            fixed.put(b, pos[i], many ? 63 : 93);
        });
    } else {
        playSound(null, {warning: 'dialog-warning', error: 'dialog-error', info: 'dialog-information'}[icon] ||
            'dialog-warning');
        const limit = Math.floor((Gdk.Screen.get_default().get_width() || 1024) * 5 / 8);
        const lines = text.replace(/\r\n/g, '\n').split('\n').map(p => p ? xpWrap(p, limit, measure) : '')
            .join('\n').split('\n');
        const tw = Math.max(...lines.map(measure));
        const th = LINE * lines.length;
        const tih = Math.max(32, th);
        const bw = btns.length * 75 + (btns.length - 1) * 6;
        const cw = Math.max(62 + tw + 8, bw + 22);
        const by = 11 + tih + 17;
        fixed.set_size_request(cw, by + 23 + 11);
        fixed.put(img, 11, 11 + Math.floor((tih - 32) / 2));
        label.set_text(lines.join('\n'));
        label.set_size_request(tw, th);
        fixed.put(label, 62, 11 + Math.floor((tih - th) / 2));
        let x = Math.floor((cw - bw) / 2);
        for (const b of btns) {
            b.set_size_request(75, 23);
            fixed.put(b, x, by);
            x += 81;
        }
    }
    let answered = false;
    const answer = i => {
        if (answered)
            return;
        answered = true;
        win.destroy();
        if (callback)
            callback(i);
    };
    btns.forEach((b, i) => b.connect('clicked', () => answer(i)));
    win.connect('delete-event', () => {
        if (escape !== null)
            answer(escape);
        return true;
    });
    win.connect('key-press-event', (w, event) => {
        if (event.get_keyval()[1] === Gdk.KEY_Escape && escape !== null) {
            answer(escape);
            return true;
        }
        return false;
    });
    win.add(fixed);
    btns[def].set_can_default(true);
    win.set_default(btns[def]);
    win.show_all();
    win.present();
    btns[def].grab_focus();
    return win;
}

/* ------------------------------------------------------------ eliminar */

function trashHasItems() {
    try {
        const info = Gio.File.new_for_uri('trash:///').query_info('trash::item-count',
            Gio.FileQueryInfoFlags.NONE, null);
        return info.get_attribute_uint32('trash::item-count') > 0;
    } catch (e) {
        return false;
    }
}

/* Delete / Shift+Delete / "Eliminar" do menu: primeiro a pergunta do XP */
function confirmDelete(dm, permanent) {
    const items = dm._fileList.filter(i => (i.isSelected || i.isKeyboardSelected) && !i.isSpecial);
    if (!items.length) {
        if (permanent && dm._fileList.some(i => (i.isSelected || i.isKeyboardSelected) && i.isTrash))
            dm.doEmptyTrash();
        return;
    }
    const many = items.length > 1;
    const name = items[0].displayName || items[0].fileName;
    let title, text, icon;
    if (many) {
        title = t('confirmMany');
        text = fmt(t(permanent ? 'killMany' : 'askMany'), items.length);
        icon = permanent ? 'kill-many' : null;
    } else if (items[0].isDirectory) {
        title = t('confirmFolder');
        text = permanent ? fmt(t('killFolder'), name, '', t('allContents')) : fmt(t('askFolder'), name);
        icon = permanent ? 'kill-folder' : null;
    } else {
        title = t('confirmFile');
        text = fmt(t(permanent ? 'killFile' : 'askFile'), name);
        icon = permanent ? 'kill-file' : null;
    }
    icon = icon || (trashHasItems() ? 'bin-full' : 'bin-empty');
    const uris = items.map(i => i.file.get_uri());
    const paths = items.map(i => i.file.get_path()).filter(p => p);
    messageBox({title, text, icon, buttons: ['yes', 'no'], def: 0, escape: 1, shell: true, many}, answer => {
        if (answer !== 0)
            return;
        if (!permanent) {
            DBusUtils.RemoteFileOperations.TrashURIsRemote(uris);
            playSound(RECYCLE);
            return;
        }
        // (de vez: aqui mesmo — o Ficheiros voltaria a perguntar, à maneira do GNOME)
        try {
            Gio.Subprocess.new(['rm', '-rf', '--', ...paths], Gio.SubprocessFlags.NONE);
        } catch (e) {
            messageBox({title, text: e.message, icon: 'error'});
        }
    });
}

/* ------------------------------------------------------------ mudar o nome */

let _editor = null;

/* (no lugar do AskRenamePopup do Zorin) */
function startRename(dm, fileItem, allowSame, text = null) {
    if (!fileItem || !fileItem.canRename)
        return;
    if (_editor)
        _editor.finish(true);
    dm.unselectAll();
    _editor = new Editor(dm, fileItem, allowSame, text);
}

var Editor = class {
    constructor(dm, item, allowSame, text) {
        ensureCss();
        this._dm = dm;
        this._allowSame = allowSame;
        this._name = item.fileName;
        this._isDir = item.isDirectory;
        this._text = text ?? item.fileName;
        this._finished = false;
        this._item = null;
        this._holder = null;
        this._rect = null;
        dm.showPopup();
        // (o desktopManager volta a ligá-lo ao item quando redesenha: updateFileItem)
        dm._renameWindow = this;
        dm._renamingFile = item.fileName;
        this.updateFileItem(item);
    }

    _build(item) {
        // largura da legenda: a da célula menos as margens
        const width = Math.max(24, item.container.get_allocated_width() -
            item._label.margin_start - item._label.margin_end);
        this._width = width;
        const probe = item._label.create_pango_layout(this._text).get_pixel_size()[0];
        this._multi = probe > width;
        if (this._multi) {
            this._editor = new Gtk.TextView({wrap_mode: Gtk.WrapMode.WORD_CHAR,
                justification: Gtk.Justification.CENTER, left_margin: 5, right_margin: 5});
            this._editor.get_style_context().add_class('zxp-rename');
            this._editor.get_buffer().set_text(this._text, -1);
            this._widget = new Gtk.Frame({shadow_type: Gtk.ShadowType.IN});
            this._widget.get_style_context().add_class('zxp-rename');
            this._widget.add(this._editor);
            this._editor.get_buffer().connect('changed', () => this._place());
        } else {
            this._editor = this._widget = new Gtk.Entry({text: this._text, width_chars: 1});
            this._editor.get_style_context().add_class('zxp-rename');
            this._editor.connect('changed', () => this._place());
            this._editor.connect('activate', () => this.finish(true));
        }
        this._editor.connect('key-press-event', (w, event) => {
            const key = event.get_keyval()[1];
            if (key === Gdk.KEY_Escape) {
                this.finish(false);
                return true;
            }
            if (key === Gdk.KEY_Return || key === Gdk.KEY_KP_Enter) {
                this.finish(true);
                return true;
            }
            return false;
        });
        this._editor.connect('focus-out-event', () => {
            if (this._finished)
                return false;
            // (logo a seguir a abrir, o foco ainda pode fugir para a grelha)
            if (GLib.get_monotonic_time() - this._since < 400000) {
                GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                    if (!this._finished && this._editor)
                        this._editor.grab_focus();
                    return GLib.SOURCE_REMOVE;
                });
                return false;
            }
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                this.finish(true);
                return GLib.SOURCE_REMOVE;
            });
            return false;
        });
        // (numa janela própria: os ícones têm as suas, que ficariam por cima)
        this._holder = new Gtk.EventBox({visible_window: true});
        this._holder.add(this._widget);
        this._holder.connect('realize', w => w.get_window().raise());
    }

    _getText() {
        if (!this._editor)
            return this._text;
        if (this._multi) {
            const buf = this._editor.get_buffer();
            return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), false);
        }
        return this._editor.get_text();
    }

    /* o item foi redesenhado (null: a sair; depois o novo) */
    updateFileItem(item) {
        if (this._finished)
            return;
        if (this._item && this._item._labelContainer)
            this._item._labelContainer.set_opacity(1);
        if (this._holder) {
            this._text = this._getText();
            const parent = this._holder.get_parent();
            if (parent)
                parent.remove(this._holder);
        }
        this._item = item;
        if (!item)
            return;
        if (!this._holder)
            this._build(item);
        this._fixed = item._grid._container;
        this._fixed.put(this._holder, 0, 0);
        this._rect = null;
        item._labelContainer.set_opacity(0);
        this._place();
        this._holder.show_all();
        this._since = GLib.get_monotonic_time();
        this._editor.grab_focus();
        // o nome sem a extensão fica selecionado, como no XP
        const stem = DesktopIconsUtil.getFileExtensionOffset(this._text, {isDirectory: this._isDir}).offset;
        if (this._multi) {
            const buf = this._editor.get_buffer();
            buf.select_range(buf.get_start_iter(), buf.get_iter_at_offset(stem));
        } else {
            this._editor.select_region(0, stem);
        }
        // clicar fora da caixa confirma (antes de o clique chegar aos ícones)
        const window = item._grid._window;
        if (this._gestureWindow !== window) {
            if (this._gesture)
                this._gesture.set_propagation_phase(Gtk.PropagationPhase.NONE);
            this._gesture = new Gtk.GestureMultiPress({widget: window, button: 0});
            this._gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE);
            this._gesture.connect('pressed', (g, n, x, y) => this._pressed(window, x, y));
            this._gestureWindow = window;
        }
        if (!this._timer) {
            this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                this._place();
                return GLib.SOURCE_CONTINUE;
            });
        }
    }

    _pressed(window, x, y) {
        if (this._finished || !this._holder || !this._rect)
            return;
        const [ok, hx, hy] = this._holder.translate_coordinates(window, 0, 0);
        if (ok && x >= hx && x < hx + this._rect[2] && y >= hy && y < hy + this._rect[3])
            return;
        this.finish(true);
    }

    _place() {
        const item = this._item;
        if (this._finished || !item || !this._holder || !item._grid || !item.container)
            return;
        const fixed = this._fixed;
        const [ok1, ix] = item.container.translate_coordinates(fixed, 0, 0);
        const [ok2, , ly] = item._label.translate_coordinates(fixed, 0, 0);
        if (!ok1 || !ok2)
            return;
        const cx = ix + item.container.get_allocated_width() / 2;
        const text = this._getText();
        let w, h, x;
        if (this._multi) {
            const lay = this._editor.create_pango_layout(text || ' ');
            lay.set_width(this._width * Pango.SCALE);
            lay.set_wrap(Pango.WrapMode.WORD_CHAR);
            w = this._width + 12;
            h = lay.get_pixel_size()[1] + 2;
            x = cx - this._width / 2 - 6;
        } else {
            const tw = this._editor.create_pango_layout(text).get_pixel_size()[0];
            w = tw + 12;
            h = 17;
            x = cx - tw / 2 - 6;
        }
        // (o texto da caixa no sítio do da legenda: moldura de 1 px)
        const rect = [Math.round(x), Math.round(ly - 1), Math.round(w), Math.round(h)];
        if (this._rect && rect.every((v, i) => v === this._rect[i]))
            return;
        this._rect = rect;
        fixed.move(this._holder, rect[0], rect[1]);
        this._holder.set_size_request(rect[2], rect[3]);
    }

    closeWindow() {
        this.finish(false);
    }

    finish(commit) {
        if (this._finished)
            return;
        const text = this._getText().replace(/\n/g, ' ').trim();
        this._finished = true;
        if (this._timer) {
            GLib.source_remove(this._timer);
            this._timer = 0;
        }
        if (this._gesture) {
            this._gesture.set_propagation_phase(Gtk.PropagationPhase.NONE);
            this._gesture = null;
        }
        if (this._item && this._item._labelContainer)
            this._item._labelContainer.set_opacity(1);
        if (this._holder)
            this._holder.destroy();
        this._holder = null;
        const dm = this._dm;
        if (dm._renameWindow === this) {
            dm._renameWindow = null;
            dm.newFolderDoRename = null;
            dm._renamingFile = null;
        }
        dm.hidePopup();
        if (_editor === this)
            _editor = null;
        if (commit && text && text !== this._name) {
            const [name, isDir, allowSame] = [this._name, this._isDir, this._allowSame];
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                applyRename(dm, name, isDir, text, allowSame);
                return GLib.SOURCE_REMOVE;
            });
        }
    }
};

function itemByName(dm, name) {
    return dm._fileList.find(f => f.fileName === name) || null;
}

function applyRename(dm, oldName, isDir, newName, allowSame) {
    const title = t('renameError');
    const again = () => startRename(dm, itemByName(dm, oldName), allowSame, newName);
    if (newName.includes('/') || newName === '.' || newName === '..') {
        messageBox({title, text: t('badChars'), icon: 'error', escape: 0}, again);
        return;
    }
    const dir = dm._desktopDir;
    const oldFile = dir.get_child(oldName);
    const target = dir.get_child(newName);
    const caseOnly = oldName.toLowerCase() === newName.toLowerCase();
    if (!caseOnly && target.query_exists(null)) {
        messageBox({title, text: fmt(t('renameFailed'), t('nameExists'), oldName), icon: 'error', escape: 0}, again);
        return;
    }
    const doIt = () => {
        if (DBusUtils.RemoteFileOperations.isAvailable) {
            DBusUtils.RemoteFileOperations.RenameURIRemote(oldFile.get_uri(), newName);
            return;
        }
        try {
            oldFile.set_display_name(newName, null);
        } catch (e) {
            messageBox({title, text: fmt(t('renameFailed'), e.message, oldName), icon: 'error', escape: 0});
        }
    };
    const ext = n => DesktopIconsUtil.getFileExtensionOffset(n, {isDirectory: false}).extension.toLowerCase();
    if (!isDir && ext(oldName) !== ext(newName)) {
        messageBox({title: plain(t('rename')), text: t('askExtension'), icon: 'warning',
            buttons: ['yes', 'no']}, answer => answer === 0 && doIt());
        return;
    }
    doIt();
}

/* ------------------------------------------------------------ menu do fundo */

function menuItem(label, callback = null) {
    const item = Gtk.MenuItem.new_with_mnemonic(mnemonic(label));
    if (callback)
        item.connect('activate', () => callback());
    return item;
}

function checkItem(label, radio = false) {
    const item = Gtk.CheckMenuItem.new_with_mnemonic(mnemonic(label));
    item.set_draw_as_radio(radio);
    return item;
}

function launch(desktopId) {
    try {
        const app = GioUnix.DesktopAppInfo.new(desktopId);
        const context = Gdk.Display.get_default().get_app_launch_context();
        context.set_timestamp(Gtk.get_current_event_time());
        app.launch([], context);
    } catch (e) {
        console.log(`Zorin XP: ${e.message}`);
    }
}

const ARRANGE = [['colName', 'NAME'], ['colSize', 'SIZE'], ['colType', 'KIND'], ['modified', 'MODIFIEDTIME']];

/* "Dispor ícones por > Nome...": arruma já por essa ordem, como no XP */
function arrangeBy(dm, order) {
    if (Prefs.getSortOrder() === order)
        dm.doSorts(true);
    else
        Prefs.setSortOrder(order);
}

/* "Colar atalho": ligações para o que está copiado ("Atalho para ...") */
function pasteShortcuts(dm) {
    for (const uri of dm._clipboardFiles || []) {
        const src = Gio.File.new_for_uri(uri);
        const path = src.get_path();
        if (!path)
            continue;
        const base = fmt(t('shortcutTo'), src.get_basename());
        let name = base;
        for (let i = 2; dm._desktopDir.get_child(name).query_exists(null); i++)
            name = `${base} (${i})`;
        try {
            dm._desktopDir.get_child(name).make_symbolic_link(path, null);
        } catch (e) {
            console.log(`Zorin XP: ${e.message}`);
        }
    }
}

/* o menu do XP no lugar do do Zorin (os itens dele continuam a existir,
   escondidos, para o resto do programa os poder usar) */
function xpMenu(dm) {
    const menu = DesktopIconsUtil.createDesktopMenu();
    const arrange = menuItem(t('arrange'));
    const sub = DesktopIconsUtil.createDesktopMenu();
    // (como no XP: sem ponto na ordem; sem as opções que ficariam desativadas)
    for (const [key, order] of ARRANGE)
        sub.add(menuItem(t(key), () => arrangeBy(dm, Enums.SortOrder[order])));
    sub.add(new Gtk.SeparatorMenuItem());
    const auto = checkItem(t('autoArrange'));
    Prefs.desktopSettings.bind('keep-arranged', auto, 'active', Gio.SettingsBindFlags.DEFAULT);
    sub.add(auto);
    arrange.set_submenu(sub);
    menu.add(arrange);
    menu.add(menuItem(t('refresh'), () => dm._updateDesktop().catch(e => console.log(`Zorin XP: ${e.message}`))));
    menu.add(new Gtk.SeparatorMenuItem());
    const paste = menuItem(t('paste'), () => dm._doPaste());
    menu.add(paste);
    const pasteLink = menuItem(t('pasteLink'), () => pasteShortcuts(dm));
    menu.add(pasteLink);
    const undo = menuItem(t('undo'), () => dm._doUndo());
    undo.get_child().set_accel(Gdk.KEY_z, Gdk.ModifierType.CONTROL_MASK);
    menu.add(undo);
    menu.add(new Gtk.SeparatorMenuItem());
    dm._zxpNew = menuItem(t('new'));
    menu.add(dm._zxpNew);
    menu.add(new Gtk.SeparatorMenuItem());
    menu.add(menuItem(t('desktopProperties'), () => launch('gnome-background-panel.desktop')));
    menu.show_all();
    const sync = GObject.BindingFlags.SYNC_CREATE;
    dm._pasteMenuItem.bind_property('sensitive', paste, 'sensitive', sync);
    dm._pasteMenuItem.bind_property('sensitive', pasteLink, 'sensitive', sync);
    dm._undoMenuItem.bind_property('visible', undo, 'visible', sync);
    dm._zxpOrigMenu = dm._menu;
    dm._menu = menu;
    prepareMenu(dm);
    const test = GLib.getenv('ZXP_DING_TEST');
    if (test) {
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
            const [, bytes] = GLib.file_get_contents(test);
            // eslint-disable-next-line no-new-func
            new Function('dm', 'Z', new TextDecoder().decode(bytes))(dm, imports.zxpDesktop);
            return GLib.SOURCE_REMOVE;
        });
    }
}

/* antes de mostrar o menu: Novo (Pasta e os modelos, com os ícones) */
function prepareMenu(dm) {
    if (!dm._zxpNew)
        return;
    const sub = DesktopIconsUtil.createDesktopMenu();
    const folder = new Gtk.ImageMenuItem({label: mnemonic(t('newFolderItem')), use_underline: true,
        image: Gtk.Image.new_from_icon_name('folder', Gtk.IconSize.MENU), always_show_image: true});
    folder.connect('activate', () => dm.doNewFolder());
    sub.add(folder);
    const entries = dm.templatesMonitor ? dm.templatesMonitor._entries : null;
    if (entries && entries.length) {
        sub.add(new Gtk.SeparatorMenuItem());
        addTemplates(dm, sub, entries);
    }
    sub.show_all();
    dm._zxpNew.set_submenu(sub);
}

function addTemplates(dm, menu, entries) {
    for (const [name, path, subDirs] of entries) {
        const label = DesktopIconsUtil.getFileExtensionOffset(name, {isDirectory: false}).basename;
        if (subDirs === null) {
            const [type] = Gio.content_type_guess(path, null);
            const item = new Gtk.ImageMenuItem({label, always_show_image: true,
                image: Gtk.Image.new_from_gicon(Gio.content_type_get_icon(type), Gtk.IconSize.MENU)});
            item.connect('activate', () => dm.templatesMonitor._activatedCB(path));
            menu.add(item);
        } else if (subDirs.length) {
            const item = new Gtk.ImageMenuItem({label: name, always_show_image: true,
                image: Gtk.Image.new_from_icon_name('folder', Gtk.IconSize.MENU)});
            const sub = DesktopIconsUtil.createDesktopMenu();
            addTemplates(dm, sub, subDirs);
            item.set_submenu(sub);
            menu.add(item);
        }
    }
}

/* (teste) desenha um widget num PNG */
function shot(widget, path) {
    const Cairo = imports.cairo;
    const w = widget.get_allocated_width(), h = widget.get_allocated_height();
    const surf = new Cairo.ImageSurface(Cairo.Format.ARGB32, w, h);
    const cr = new Cairo.Context(surf);
    cr.setSourceRGB(0.23, 0.43, 0.65);
    cr.paint();
    widget.draw(cr);
    surf.writeToPNG(path);
    cr.$dispose();
}
