"""Zorin XP — Nautilus with the look of the Windows XP Explorer.

A nautilus-python extension (installed in ~/.local/share/nautilus-python/
extensions): it runs inside Nautilus and, when Nautilus opens a window,
rearranges it like XP's Explorer, without changing what Nautilus does:

  caption    folder icon + name on the left, window buttons
  menus      Ficheiro  Editar  Ver  Favoritos  Ferramentas  Ajuda
  toolbar    Retroceder  Avançar  Acima | Procurar  Pastas | Vistas
  address    Endereço [icon  path]  [→ Ir para]
  left       the blue task pane, with the places in a section

Nautilus's own bars stay hidden (they are still there: search shows them
again); the menus and buttons call the actions Nautilus already has. The
images come from the GTK theme (generated from shell32.dll/shellstyle.dll).
"""
import collections
import json
import math
import os

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Graphene', '1.0')
from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, GObject, Graphene, Gtk, Nautilus, Pango  # noqa: E402

ASSETS = os.path.expanduser('~/.themes/WindowsXP-Luna/gtk-4.0/assets')
BRAND_SIZE = 22
BRAND_FRAME_MS = 40

TEXTS = {
    'pt': {
        'file': 'Ficheiro', 'edit': 'Editar', 'view': 'Ver', 'favorites': 'Favoritos',
        'tools': 'Ferramentas', 'help': 'Ajuda',
        'new-window': 'Nova janela', 'new-folder': 'Nova pasta', 'properties': 'Propriedades',
        'rename': 'Mudar o nome',
        'close': 'Fechar', 'undo': 'Anular', 'redo': 'Refazer', 'cut': 'Cortar',
        'copy': 'Copiar', 'paste': 'Colar', 'select-all': 'Selecionar tudo',
        'invert': 'Inverter seleção', 'folders': 'Pastas', 'toggle-view': 'Ícones / Lista',
        'hidden': 'Mostrar ficheiros ocultos', 'refresh': 'Actualizar',
        'arrange': 'Dispor ícones por', 'arrange-name': 'Nome', 'arrange-size': 'Tamanho',
        'arrange-type': 'Tipo', 'arrange-modified': 'Modificado',
        'add-favorite': 'Adicionar aos favoritos', 'options': 'Opções de pastas...',
        'help-topics': 'Tópicos de ajuda', 'about': 'Acerca do Nautilus',
        'back': 'Retroceder', 'forward': 'Avançar', 'up': 'Acima', 'search': 'Procurar',
        'views': 'Vistas', 'address': 'Endereço', 'go': 'Ir para', 'places': 'Locais',
        'thumbnails': 'Miniaturas', 'tiles': 'Mosaicos', 'icons': 'Ícones', 'list': 'Lista',
        'details': 'Detalhes',
        'col-name': 'Nome', 'col-size': 'Tamanho', 'col-type': 'Tipo',
        'col-date_modified': 'Data da modificação', 'col-date_created': 'Data de criação',
        'col-date_accessed': 'Data do último acesso', 'col-owner': 'Proprietário',
        'col-permissions': 'Atributos', 'folder-type': 'Pasta de ficheiros',
        'file-tasks': 'Tarefas de pastas e ficheiros', 'other-places': 'Outros locais',
        'details': 'Detalhes', 'task-new-folder': 'Criar uma nova pasta',
        'task-rename-file': 'Mudar o nome a este ficheiro', 'task-rename-folder': 'Mudar o nome a esta pasta',
        'task-move-file': 'Mover este ficheiro', 'task-move-folder': 'Mover esta pasta',
        'task-move-many': 'Mover os itens seleccionados',
        'task-copy-file': 'Copiar este ficheiro', 'task-copy-folder': 'Copiar esta pasta',
        'task-copy-many': 'Copiar os itens seleccionados',
        'task-delete-file': 'Eliminar este ficheiro', 'task-delete-folder': 'Eliminar esta pasta',
        'task-delete-many': 'Eliminar os itens seleccionados',
        'n-selected': '{} itens seleccionados.', 'dimensions': 'Dimensões: {} x {}',
        'total-size': 'Tamanho total do ficheiro: {}', 'new-folder-name': 'Nova pasta',
        'music-tasks': 'Tarefas de músicas', 'pictures-tasks': 'Tarefas de imagens',
        'videos-tasks': 'Tarefas de vídeos', 'play-all': 'Reproduzir tudo',
        'slideshow': 'Ver como apresentação de diapositivos',
        'set-background': 'Definir como fundo do ambiente de trabalho',
        'size-line': 'Tamanho: {}', 'modified-line': 'Data da modificação: {}',
        'months': ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto',
                   'Setembro', 'Outubro', 'Novembro', 'Dezembro'],
        'weekdays': ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira',
                     'sábado', 'domingo'],
        'long-date': '{wd}, {d} de {m} de {y}, {t}',
        # (shell32.dll: dialogs 1011-1013, strings 16722, 16723, 4112)
        'delete': 'Eliminar', 'yes': '_Sim', 'no': '_Não',
        'confirm-file': 'Confirmar eliminação de ficheiro(s)',
        'confirm-folder': 'Confirmar eliminação de pasta(s)',
        'confirm-many': 'Confirmar eliminação de vários ficheiros',
        'ask-file': "Tem a certeza de que pretende mandar '{}' para a 'Reciclagem'?",
        'ask-folder': "Tem a certeza de que pretende remover a pasta '{}' e mover todo o conteúdo "
                      "para a 'Reciclagem'?",
        'ask-many': "Tem a certeza de que pretende mandar estes {} itens para a 'Reciclagem'?",
        # (delete permanently: Shift+Delete, in the Recycle Bin — shell32 12295, 66)
        'kill-file': "Tem a certeza de que pretende eliminar '{}'?",
        'kill-folder': "Tem a certeza de que pretende remover a pasta '{}' e todo o seu conteúdo?",
        'kill-many': 'Tem a certeza de que pretende eliminar estes {} itens?',
        'ask-extension': 'Se alterar uma extensão de nome de ficheiro, poderá não ser possível '
                         'utilizar o ficheiro.\n\nTem a certeza de que pretende alterá-la?',
        'recent': 'Recentes',
        'shortcuts': 'Atalhos', 'add-shortcut': 'Adicionar atalho', 'open-terminal': 'Abrir num terminal',
        'remove-shortcut': 'Remover atalho', 'open': 'Abrir',
        'open-window': 'Abrir numa nova janela',
    },
    'en': {
        'file': 'File', 'edit': 'Edit', 'view': 'View', 'favorites': 'Favorites',
        'tools': 'Tools', 'help': 'Help',
        'new-window': 'New Window', 'new-folder': 'New Folder', 'properties': 'Properties',
        'rename': 'Rename',
        'close': 'Close', 'undo': 'Undo', 'redo': 'Redo', 'cut': 'Cut',
        'copy': 'Copy', 'paste': 'Paste', 'select-all': 'Select All',
        'invert': 'Invert Selection', 'folders': 'Folders', 'toggle-view': 'Icons / List',
        'hidden': 'Show Hidden Files', 'refresh': 'Refresh',
        'arrange': 'Arrange Icons by', 'arrange-name': 'Name', 'arrange-size': 'Size',
        'arrange-type': 'Type', 'arrange-modified': 'Modified',
        'add-favorite': 'Add to Favorites', 'options': 'Folder Options...',
        'help-topics': 'Help Topics', 'about': 'About Nautilus',
        'back': 'Back', 'forward': 'Forward', 'up': 'Up', 'search': 'Search',
        'views': 'Views', 'address': 'Address', 'go': 'Go', 'places': 'Places',
        'thumbnails': 'Thumbnails', 'tiles': 'Tiles', 'icons': 'Icons', 'list': 'List',
        'details': 'Details',
        'col-name': 'Name', 'col-size': 'Size', 'col-type': 'Type',
        'col-date_modified': 'Date Modified', 'col-date_created': 'Date Created',
        'col-date_accessed': 'Date Accessed', 'col-owner': 'Owner',
        'col-permissions': 'Attributes', 'folder-type': 'File Folder',
        'file-tasks': 'File and Folder Tasks', 'other-places': 'Other Places',
        'details': 'Details', 'task-new-folder': 'Make a new folder',
        'task-rename-file': 'Rename this file', 'task-rename-folder': 'Rename this folder',
        'task-move-file': 'Move this file', 'task-move-folder': 'Move this folder',
        'task-move-many': 'Move the selected items',
        'task-copy-file': 'Copy this file', 'task-copy-folder': 'Copy this folder',
        'task-copy-many': 'Copy the selected items',
        'task-delete-file': 'Delete this file', 'task-delete-folder': 'Delete this folder',
        'task-delete-many': 'Delete the selected items',
        'n-selected': '{} items selected.', 'dimensions': 'Dimensions: {} x {}',
        'total-size': 'Total File Size: {}', 'new-folder-name': 'New Folder',
        'music-tasks': 'Music Tasks', 'pictures-tasks': 'Picture Tasks',
        'videos-tasks': 'Video Tasks', 'play-all': 'Play all',
        'slideshow': 'View as a slide show',
        'set-background': 'Set as desktop background',
        'size-line': 'Size: {}', 'modified-line': 'Date Modified: {}',
        'months': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                   'September', 'October', 'November', 'December'],
        'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'long-date': '{wd}, {m} {d}, {y}, {t}',
        'delete': 'Delete', 'yes': '_Yes', 'no': '_No',
        'confirm-file': 'Confirm File Delete', 'confirm-folder': 'Confirm Folder Delete',
        'confirm-many': 'Confirm Multiple File Delete',
        'ask-file': "Are you sure you want to send '{}' to the Recycle Bin?",
        'ask-folder': "Are you sure you want to remove the folder '{}' and move all its contents "
                      "to the Recycle Bin?",
        'ask-many': "Are you sure you want to send these {} items to the Recycle Bin?",
        'kill-file': "Are you sure you want to delete '{}'?",
        'kill-folder': "Are you sure you want to remove the folder '{}' and all its contents?",
        'kill-many': 'Are you sure you want to delete these {} items?',
        'ask-extension': 'If you change a file name extension, the file might become unusable.'
                         '\n\nAre you sure you want to change it?',
        'recent': 'Recent',
        'shortcuts': 'Shortcuts', 'add-shortcut': 'Add Shortcut', 'open-terminal': 'Open in Terminal',
        'remove-shortcut': 'Remove Shortcut', 'open': 'Open',
        'open-window': 'Open in New Window',
    },
}
# XP's views on top of Nautilus's two views (grid = 2, list = 1 in the
# slot.files-view-mode action) and the icon sizes it has: the grid starts at
# 48 px (XP uses 32 in Icons), XP's thumbnails are 96
VIEW_MODES = {
    'thumbnails': {'view': 2, 'zoom': 'medium', 'captions': ['none', 'none', 'none']},
    'tiles': {'view': 2, 'zoom': 'small', 'captions': ['zxp_tile', 'none', 'none']},
    'icons': {'view': 2, 'zoom': 'small', 'captions': ['none', 'none', 'none']},
    'list': {'view': 2, 'zoom': 'small', 'captions': ['none', 'none', 'none']},
    'details': {'view': 1, 'zoom': 'small', 'columns': ['name', 'zxp_size', 'zxp_type', 'zxp_date']},
}
DEFAULT_VIEW = 'icons'
# steps of the Explorer's grids (measured in XP captures): Tiles 218 x 56,
# Thumbnails 125 x 139 (96 px frame), Icons 75 (32 px icons)
TILE_WIDTH = 218
THUMB_PITCH = 125
ICON_PITCH = 75
ICON_SIZE = 32
# Thumbnails: XP's icons only go up to 48 px — as in XP, they are not
# stretched (they stay at 48 in the centre of the frame); only images get a
# thumbnail. In Icons and Tiles images get the type icon, as in XP
THUMB_ICON = 48
PITCHES = {'tiles': TILE_WIDTH, 'thumbnails': THUMB_PITCH, 'icons': ICON_PITCH}
# width of the name below the icon (the column minus 2 px on each side)
NAME_WIDTHS = {'thumbnails': THUMB_PITCH - 4, 'icons': ICON_PITCH - 4}
# the rename box in Icons and Thumbnails (measured in an XP capture): centred
# on the item, the text + 5 px on each side + the 1 px outline; it grows on
# both sides while typing, up to 66 px of text (78 px box), then breaks into
# more lines; 13 px lines, 2 px above and below
EDIT_TEXT_W = 66
EDIT_PAD = 5
EDIT_LINE = 13
# List as in XP (measured in an XP capture): the grid on its side — columns
# filled from top to bottom and scrolled sideways (with Details, the only view
# that scrolls sideways), all as wide as the folder's longest name: the 16 px
# icon at the edge, the name 18 px from it, 8 px after the longest one, 17 px rows
LIST_ROW = 17
LIST_ICON = 16
LIST_TEXT_X = 18
LIST_GAP = 8
TYPE_ICON_SIZES = {'thumbnails': THUMB_ICON, 'tiles': THUMB_ICON, 'icons': ICON_SIZE, 'list': LIST_ICON}
# views whose icon is smaller than Nautilus's smallest grid icon (48 px), and
# the icon box Nautilus asks for at each zoom (given back when leaving them)
SMALL_ICONS = {'icons': ICON_SIZE, 'list': LIST_ICON}
ZOOM_ICON_BOX = {'small': 48, 'medium': 96}
# selection as in XP (ImageList ILD_BLEND50, measured in an XP capture):
# pixels with alpha >= 128 go halfway to the highlight colour (with
# premultiplied alpha, rounded up); the others (shadows) stay the same
HIGHLIGHT = (0x31, 0x6A, 0xC5)
# Details: the column the list is sorted by with a light grey background from
# top to bottom, as in XP (measured); the header strip is the theme's
# (src/gtk/40-libadwaita.css.in, ".nautilus-list-view columnview")
SORTED_COLUMN_BG = '#F7F7F7'
HEADER_BAND = ('linear-gradient(to bottom, #EEEAD8 0, #EEEAD8 17px, #E2DECD 17px, #E2DECD 18px, '
               '#D6D2C2 18px, #D6D2C2 19px, #CBC7B8 19px, #CBC7B8 20px, transparent 20px)')
# "Outros locais" (Other Places), in this order (Nautilus's other places go;
# the bookmarks go to the "Atalhos" section, which only shows if there are any)
OTHER_PLACES = ('home', 'documents', 'recent', 'starred', 'downloads')
SECTION_MOUNTS = 2                 # NautilusGtkPlacesSectionType (unidades ligadas)
BOOKMARKS = os.path.join(GLib.get_user_config_dir(), 'gtk-3.0', 'bookmarks')
# icons chosen for the Shortcuts (address -> icon name), only there: the
# real folders stay as they are; mounted disks get the disk icon by themselves
SHORTCUT_ICONS = os.path.join(GLib.get_user_data_dir(), 'zorin-xp', 'shortcut-icons.json')
NETWORK_FS = ('cifs', 'smb3', 'smbfs', 'nfs', 'nfs4', 'fuse.sshfs', 'sshfs', '9p', 'vboxsf', 'davfs')
OPEN_NORMAL = 1                    # NautilusOpenFlags
# widths of the Details columns in the Explorer (measured)
COLUMN_WIDTHS = {'name': 179, 'size': 97, 'type': 119, 'date_modified': 121,
                 'zxp_size': 97, 'zxp_type': 119, 'zxp_date': 121}
RIGHT_ALIGNED = ('size', 'zxp_size')
STATE_FILE = os.path.join(GLib.get_user_data_dir(), 'zorin-xp', 'explorer.ini')
# "Dispor ícones por" (background menu): Nautilus's own sorting (the
# view.sort action, target (attribute, reversed)), with the dot on the chosen one
ARRANGE = (('name', ('name', False)), ('size', ('size', False)), ('type', ('type', False)),
           ('modified', ('date_modified', True)))
SIDEBAR_ICONS = {'document-open-recent': 'folder-recent', 'starred': 'user-bookmarks'}
# the same for the title, the address and the taskbar (explorerIcons.js)
SCHEME_ICONS = {'recent': 'folder-recent', 'starred': 'user-bookmarks'}
# the Explorer's click when opening a folder (XP's "Iniciar navegação")
NAV_SOUND = os.path.join(GLib.get_user_data_dir(), 'sounds', 'WindowsXP', 'xp', 'Windows XP Start.wav')
NAV_QUIET_MS = 300
# the sound of sending to the Recycle Bin ("Esvaziar a Reciclagem" in XP)
TRASH_SOUND = os.path.join(GLib.get_user_data_dir(), 'sounds', 'WindowsXP', 'xp', 'Windows XP Recycle.wav')
# the Nautilus menu items that open its own windows: XP's instead
SWAPPED_ACTIONS = {'view.new-folder': 'xp.new-folder', 'view.rename': 'xp.rename',
                   'view.move-to-trash': 'xp.delete',
                   'view.delete-permanently-menu-item': 'xp.delete-permanently',
                   'view.delete-from-trash': 'xp.delete-permanently'}
# Nautilus's column -> ours, with XP's formats (Recent, searches)
COLUMN_TWINS = {'size': 'zxp_size', 'type': 'zxp_type', 'date_modified': 'zxp_date'}
# preview in Details: at the pane's width (the pane does not grow)
PREVIEW_MAX = (200, 200)
PREVIEW_CACHE = os.path.join(GLib.get_user_cache_dir(), 'zorin-xp', 'details-preview')

LANG = next((l[:2] for l in GLib.get_language_names() if l[:2] in TEXTS), 'en')
T = TEXTS[LANG]


def walk(widget):
    yield widget
    child = widget.get_first_child()
    while child:
        yield from walk(child)
        child = child.get_next_sibling()


def find(widget, type_name):
    """First descendant with this GObject type (the type's name in Python
    changes with the imported modules; the GType's does not)."""
    return next((w for w in walk(widget) if w.__gtype__.name == type_name), None)


def asset(name):
    path = os.path.join(ASSETS, f'{name}.png')
    return path if os.path.exists(path) else None


def image(name, fallback_icon, size=24):
    path = asset(name)
    img = Gtk.Image.new_from_file(path) if path else Gtk.Image.new_from_icon_name(fallback_icon)
    img.set_pixel_size(size)
    return img


class XpExplorer:
    """Rearranges a Nautilus window."""

    def __init__(self, win):
        self.win = win
        self.split = find(win, 'AdwOverlaySplitView')
        if not self.split or win.get_content() is None:
            return
        self.content_tv = self.split.get_content()
        self.sidebar_tv = self.split.get_sidebar()
        self.tabs = find(self.content_tv, 'AdwTabView')
        win.add_css_class('zxp-explorer')
        self._mode = load_view_mode()
        # (for style rules for this window only: _sort_band)
        self._css_id = f'zxp-win-{id(self)}'
        win.add_css_class(self._css_id)
        # Nautilus's "New Folder" window (it asks for the name first): XP's instead
        self._toplevels = Gtk.Window.get_toplevels()
        self._toplevels.connect('items-changed', self._new_toplevels)
        self._tiles = self._mode == 'tiles'
        self._thumbs = self._mode == 'thumbnails'
        self._editor = None
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed', self._keys)
        win.add_controller(keys)
        # no zoom in any view, as in XP's Explorer: without the shortcuts
        # (Ctrl++, Ctrl+-, Ctrl+0) and without Ctrl+wheel (the size comes from the chosen view)
        app = win.get_application()
        if app is not None:
            for action in ('view.zoom-in', 'view.zoom-out', 'view.zoom-standard'):
                app.set_accels_for_action(action, [])
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL,
                                           propagation_phase=Gtk.PropagationPhase.CAPTURE)
        scroll.connect('scroll', lambda c, _dx, _dy: bool(
            c.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK))
        win.add_controller(scroll)

        self._actions()
        # Nautilus's bars stay hidden (search shows them again)
        self.content_tv.set_reveal_top_bars(False)
        self.content_tv.set_reveal_bottom_bars(False)
        if isinstance(self.sidebar_tv, Adw.ToolbarView):
            header = find(self.sidebar_tv, 'AdwHeaderBar')
            if header:
                header.set_visible(False)

        view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)
        view.add_top_bar(self._caption())
        view.add_top_bar(self._menubar())
        view.add_top_bar(self._toolbar())
        view.add_top_bar(self._addressbar())
        content = win.get_content()
        win.set_content(None)
        view.set_content(content)
        win.set_content(view)

        self._task_pane()
        if self.tabs:
            self.tabs.connect('notify::selected-page', lambda *_: self._follow_slot())
        self._follow_slot()

    # ------------------------------------------------------------- actions
    def _slot(self):
        page = self.tabs.get_selected_page() if self.tabs else None
        child = page.get_child() if page else None
        return find(child, 'NautilusWindowSlot') if child else None

    def _files_view(self):
        slot = self._slot()
        return find(slot, 'NautilusFilesView') if slot else None

    def _actions(self):
        group = Gio.SimpleActionGroup()

        def add(name, fn):
            a = Gio.SimpleAction.new(name, None)
            a.connect('activate', lambda *_: fn())
            group.add_action(a)

        def on_view(action):
            def run():
                v = self._files_view()
                if v:
                    v.activate_action(f'view.{action}', None)
            return run

        for name in ('properties', 'cut', 'copy', 'paste', 'select-all',
                     'invert-selection', 'show-hidden-files'):
            add(name, on_view(name))
        add('new-folder', lambda: self._new_folder())
        add('rename', lambda: self._rename_selected())
        add('delete', lambda: self._confirm_delete())
        add('delete-permanently', lambda: self._confirm_delete(permanent=True))

        def on_slot(action):
            def run():
                s = self._slot()
                if s:
                    s.activate_action(f'slot.{action}', None)
            return run
        add('toggle-view', on_slot('files-view-mode-toggle'))
        mode = Gio.SimpleAction.new_stateful('view-mode', GLib.VariantType.new('s'),
                                             GLib.Variant('s', load_view_mode()))
        mode.connect('activate', lambda a, v: self._set_view_mode(a, v.get_string()))
        group.add_action(mode)
        # (win.toggle-sidebar only works with a narrow window)
        add('toggle-folders', lambda: self.split.set_show_sidebar(not self.split.get_show_sidebar()))
        add('go', self._go)
        add('open-terminal', self._open_terminal)

        def add_uri(name, fn):
            a = Gio.SimpleAction.new(name, GLib.VariantType.new('s'))
            a.connect('activate', lambda _a, v: fn(v.get_string()))
            group.add_action(a)
        add_uri('add-shortcut', self._add_shortcut)
        add_uri('remove-shortcut', self._remove_shortcut)
        add_uri('open-place', self._open_place)
        add_uri('open-place-window', lambda uri: Gio.Application.get_default().open(
            [Gio.File.new_for_uri(uri)], ''))
        self.win.insert_action_group('xp', group)

    # ------------------------------------------------------------ bars
    def _caption(self):
        self.title_icon = Gtk.Image(pixel_size=16)
        title = Gtk.Label(xalign=0, css_classes=['title'], ellipsize=3)
        self.win.bind_property('title', title, 'label', GObject.BindingFlags.SYNC_CREATE)
        box = Gtk.Box(spacing=4, css_classes=['zxp-explorer-title'])
        box.append(self.title_icon)
        box.append(title)
        header = Adw.HeaderBar(title_widget=Adw.Bin())
        header.pack_start(box)
        return header

    def _menubar(self):
        def section(*items):
            m = Gio.Menu()
            for label, action in items:
                m.append(label, action)
            return m

        def menu(*sections):
            m = Gio.Menu()
            for s in sections:
                m.append_section(None, s)
            return m

        model = Gio.Menu()
        model.append_submenu(T['file'], menu(
            section((T['new-window'], 'app.new-window'), (T['new-folder'], 'xp.new-folder')),
            section((T['delete'], 'xp.delete'), (T['rename'], 'xp.rename'),
                    (T['properties'], 'xp.properties')),
            section((T['close'], 'win.close-current-view'))))
        model.append_submenu(T['edit'], menu(
            section((T['undo'], 'win.undo'), (T['redo'], 'win.redo')),
            section((T['cut'], 'xp.cut'), (T['copy'], 'xp.copy'), (T['paste'], 'xp.paste')),
            section((T['select-all'], 'xp.select-all'), (T['invert'], 'xp.invert-selection'))))
        model.append_submenu(T['view'], menu(
            section((T['folders'], 'xp.toggle-folders')),
            self._views_menu(),
            section((T['hidden'], 'xp.show-hidden-files')),
            section((T['refresh'], 'win.reload'))))
        model.append_submenu(T['favorites'], menu(
            section((T['add-favorite'], 'win.bookmark-current-location'))))
        model.append_submenu(T['tools'], menu(section((T['options'], 'app.preferences'))))
        model.append_submenu(T['help'], menu(
            section((T['help-topics'], 'app.help'), (T['about'], 'app.about'))))
        bar = Gtk.PopoverMenuBar.new_from_model(model)
        bar.set_hexpand(True)
        box = Gtk.Box(css_classes=['zxp-explorer-menubar'])
        box.append(bar)
        box.append(self._brand())
        return box

    def _views_menu(self):
        m = Gio.Menu()
        for key in VIEW_MODES:
            m.append(T[key], f'xp.view-mode::{key}')
        return m

    def _set_view_mode(self, action, key):
        conf = VIEW_MODES.get(key)
        slot = self._slot()
        if not conf or not slot:
            return
        action.set_state(GLib.Variant('s', key))
        save_view_mode(key)
        # (now, before Nautilus swaps the cells' images: _thumb_picture)
        self._mode = key
        self._tiles = key == 'tiles'
        self._thumbs = key == 'thumbnails'
        prefs = Gio.Settings.new('org.gnome.nautilus.preferences')
        if conf['view'] == 2:
            icons = Gio.Settings.new('org.gnome.nautilus.icon-view')
            icons.set_string('default-zoom-level', conf['zoom'])
            icons.set_strv('captions', conf['captions'])
            prefs.set_string('default-folder-viewer', 'icon-view')
        else:
            lst = Gio.Settings.new('org.gnome.nautilus.list-view')
            lst.set_string('default-zoom-level', conf['zoom'])
            lst.set_strv('default-visible-columns', conf['columns'])
            # XP's columns right after the name, in the Explorer's order
            order = [c for c in lst.get_strv('default-column-order') if c not in conf['columns']]
            lst.set_strv('default-column-order', conf['columns'] + order)
            prefs.set_string('default-folder-viewer', 'list-view')
        if conf['view'] == 1:
            # the default columns only apply to a new view
            slot.activate_action('slot.files-view-mode', GLib.Variant('u', 2))
        slot.activate_action('slot.files-view-mode', GLib.Variant('u', conf['view']))

        def settle():
            self._sync_tiles(key)
            return False
        GLib.idle_add(settle)

    def _sync_tiles(self, key=None):
        """Tiles: the grid's cells lying down — icon on the left, name, type and
        size beside it, left-aligned (Nautilus's grid only has them standing).
        Cells are recycled and created while scrolling, so the grid is
        followed and every new cell is fixed."""
        if key is not None:
            self._mode = key
            self._tiles = key == 'tiles'
            self._thumbs = key == 'thumbnails'
        view = self._files_view()
        # XP does not have Nautilus's floating bar ("… selected (303.5 kB)")
        bar = find(view, 'NautilusFloatingBar') if view else None
        if bar is not None and bar.get_child_visible():
            bar.set_child_visible(False)
        # nor the "Folder is empty" notice: in XP an empty folder stays blank
        # (hidden for good, so clicks reach the view underneath)
        for page in (w for w in walk(view) if w.__gtype__.name == 'AdwStatusPage') if view else ():
            if page.get_child_visible():
                page.set_child_visible(False)
        if view:
            slot = getattr(self, '_slot_obj', None)
            kind = self._folder_kind(slot.get_property('location') if slot else None)
            for k in ('music', 'pictures', 'videos'):
                (view.add_css_class if k == kind else view.remove_css_class)(f'zxp-wm-{k}')
        if view:
            # (List does not have the Details header strip: CSS)
            (view.add_css_class if self._mode == 'list' else view.remove_css_class)('zxp-list')
        columns = find(view, 'GtkColumnView') if view else None
        if columns:
            self._sync_columns(columns)
        grid = find(view, 'GtkGridView') if view else None
        if not grid:
            return
        (view.add_css_class if self._tiles else view.remove_css_class)('zxp-tiles')
        (view.add_css_class if self._thumbs else view.remove_css_class)('zxp-thumbs')
        (view.add_css_class if self._mode == 'icons' else view.remove_css_class)('zxp-icons')
        self._tile_columns(grid)
        if not getattr(grid, '_zxp_watch', False):
            grid._zxp_watch = True
            scroller = grid.get_parent()
            if scroller:
                scroller.connect('notify::width', lambda *_: self._tile_columns(grid))
                self._tile_width_cb(scroller, grid)
            # new cells appear while scrolling (sideways in List) and when the
            # folder finishes loading
            for adj in (grid.get_vadjustment(), grid.get_hadjustment()):
                if adj:
                    adj.connect('value-changed', lambda *_: self._tile_cells(grid))
                    adj.connect('changed', lambda *_: GLib.idle_add(lambda: self._tile_cells(grid)))
            # (List: the rows per column follow the view's height — on its side,
            # the grid's vertical page is that height)
            vadj = grid.get_vadjustment()
            if vadj:
                vadj.connect('notify::page-size', lambda *_: getattr(self, '_mode', None) == 'list' and
                             GLib.idle_add(lambda: self._tile_columns(grid)))
            # (List: the columns follow the folder's names)
            grid.connect('notify::model', lambda *_: self._watch_list_model(grid))
            self._watch_list_model(grid)
        self._on_bind(grid.get_factory(), grid, self._tile_cells)
        self._tile_cells(grid)
        tries = [10]

        def again():
            self._tile_cells(grid)
            tries[0] -= 1
            return tries[0] > 0
        GLib.timeout_add(150, again)

    def _on_bind(self, factory, view, update):
        """update(view) after the list puts files into the cells (new cells when
        the folder reloads, or recycled ones), once per cycle."""
        if factory is None or getattr(factory, '_zxp_bind', False):
            return
        factory._zxp_bind = True

        def bound(*_):
            if not getattr(view, '_zxp_bind_idle', 0):
                def run():
                    view._zxp_bind_idle = 0
                    update(view)
                    return False
                view._zxp_bind_idle = GLib.idle_add(run)
        factory.connect_after('bind', bound)

    def _sync_columns(self, cv):
        """Details: column titles and widths as in the Explorer. XP's List has no
        header."""
        header = next((w for w in walk(cv) if w.get_css_name() == 'header'), None)
        if header is not None:
            header.set_visible(getattr(self, '_mode', None) != 'list')
        cols = cv.get_columns()
        # in Recent (and searches) Nautilus uses its own columns: ours in the same
        # place, with XP's formats ("31 KB", "Imagem PNG")
        by_id = {cols.get_item(i).get_id(): cols.get_item(i) for i in range(cols.get_n_items())}
        for cid, tid in COLUMN_TWINS.items():
            col, twin = by_id.get(cid), by_id.get(tid)
            if col is not None and twin is not None and col.get_visible() and not twin.get_visible():
                pos = next(i for i in range(cols.get_n_items()) if cols.get_item(i) == col)
                twin.set_visible(True)
                col.set_visible(False)
                cv.insert_column(pos, twin)
        recent = self._location_scheme() == 'recent'
        # titles cut with "..." when they do not fit with the arrow (as in XP),
        # redone when a column's width or the sorting changes
        if not getattr(cv, '_zxp_titles', False):
            cv._zxp_titles = True
            sorter = cv.get_sorter()
            if sorter is not None:
                sorter.connect('changed', lambda *_: self._header_titles(cv))
            cols.connect('items-changed', lambda *_: self._header_titles(cv))
            hadj = cv.get_hadjustment()
            if hadj is not None:
                hadj.connect('value-changed', lambda *_: self._next_frames(cv, lambda: self._sort_band(cv), 2))
        for i in range(cols.get_n_items()):
            col = cols.get_item(i)
            if not getattr(col, '_zxp_titles', False):
                col._zxp_titles = True
                col.connect('notify::fixed-width', lambda *_: self._header_titles(cv))
        for i in range(cols.get_n_items()):
            col = cols.get_item(i)
            self._on_bind(col.get_factory(), cv, self._align_cells)
            cid = col.get_id() or ''
            if cid == 'starred':
                # (XP has no stars; the column stretched the rows and Nautilus shows it
                # again when it loads each folder)
                col.set_visible(False)
                if not getattr(col, '_zxp_hide', False):
                    col._zxp_hide = True
                    col.connect('notify::visible',
                                lambda c, _p: c.get_visible() and c.set_visible(False))
                continue
            title = T.get(f'col-{cid}')
            if title and col.get_title() != title:
                col.set_title(title)
            width = COLUMN_WIDTHS.get(cid)
            if cid == 'name' and (getattr(self, '_mode', None) == 'list' or recent):
                # List: the whole name, as in XP (the column takes the width); in
                # Recent the names are long: too
                col.set_fixed_width(-1)
                col.set_expand(True)
            elif width:
                col.set_expand(False)
                col.set_resizable(True)
                if col.get_fixed_width() <= 0:
                    col.set_fixed_width(width)
        self._header_titles(cv)
        self._align_cells(cv)
        if not getattr(cv, '_zxp_watch', False):
            cv._zxp_watch = True
            adj = cv.get_vadjustment()
            if adj:
                adj.connect('value-changed', lambda *_: self._align_cells(cv))
                adj.connect('changed', lambda *_: GLib.idle_add(lambda: self._align_cells(cv)))
            tries = [10]

            def again():
                self._align_cells(cv)
                tries[0] -= 1
                return tries[0] > 0
            GLib.timeout_add(150, again)

    def _header_titles(self, cv):
        """The Details header titles as in XP: what does not fit (with the sort
        arrow) is cut with "..." instead of pushing the arrow out. First the
        whole title, so GTK says whether it fits; once drawn, the cut to the
        space that is left."""
        header = next((w for w in walk(cv) if w.get_css_name() == 'header'), None)
        if header is None:
            return
        labels = [w for w in walk(header) if isinstance(w, Gtk.Label)]
        for lbl in labels:
            if lbl.get_label() != getattr(lbl, '_zxp_text', None):
                lbl._zxp_name = lbl.get_label()     # (set by GTK: the title)
            if lbl.get_label() != lbl._zxp_name:
                lbl.set_label(lbl._zxp_name)
            lbl._zxp_text = lbl._zxp_name
            lbl.set_ellipsize(Pango.EllipsizeMode.END)

        def cut():
            for lbl in labels:
                if lbl.get_width() > 0 and lbl.get_layout().is_ellipsized():
                    text = xp_wrap(lbl._zxp_name, lbl.get_width(),
                                   lambda t: lbl.create_pango_layout(t).get_pixel_size()[0], 1)
                    lbl._zxp_text = text
                    lbl.set_label(text)
            self._sort_band(cv)
        self._next_frames(cv, cut)

    def _next_frames(self, widget, fn, frames=12):
        """fn() on the next frames (~0.2 s): the positions are only right after
        GTK redoes the layout, which may take more than one."""
        widget._zxp_frames = frames
        widget._zxp_frame_fn = fn
        if getattr(widget, '_zxp_tick', 0):
            return

        def tick(_w, _clock):
            widget._zxp_frame_fn()
            widget._zxp_frames -= 1
            if widget._zxp_frames > 0:
                return GLib.SOURCE_CONTINUE
            widget._zxp_tick = 0
            return GLib.SOURCE_REMOVE
        widget._zxp_tick = widget.add_tick_callback(tick)

    def _sort_band(self, cv):
        """Details: the column the list is sorted by with XP's light grey
        background, as wide as its title and from top to bottom (also where
        there are no more files). It is the list's own background, below the
        rows, with the header strip on top; set in a stylesheet for this
        window only, with the column's position."""
        css = ''
        header = next((w for w in walk(cv) if w.get_css_name() == 'header'), None)
        if getattr(self, '_mode', None) == 'details' and header is not None:
            for btn in walk(header):
                if btn.get_css_name() != 'button' or btn.get_width() <= 0:
                    continue
                ind = next((w for w in walk(btn) if w.get_css_name() == 'sort-indicator'), None)
                if ind is None or not (ind.has_css_class('ascending') or ind.has_css_class('descending')):
                    continue
                ok, r = btn.compute_bounds(cv)
                if ok:
                    css = (f'window.{self._css_id} .nautilus-list-view columnview {{ '
                           f'background-image: {HEADER_BAND}, linear-gradient({SORTED_COLUMN_BG}, '
                           f'{SORTED_COLUMN_BG}); background-size: 100% 20px, {round(r.size.width)}px 100%; '
                           f'background-position: 0 0, {round(r.origin.x)}px 0; '
                           f'background-repeat: no-repeat; }}')
                break
        if css == getattr(self, '_band_css', None):
            return
        self._band_css = css
        if getattr(self, '_band_provider', None) is None:
            self._band_provider = Gtk.CssProvider()
            display = self.win.get_display()
            # (above the theme, which comes in as a user stylesheet)
            Gtk.StyleContext.add_provider_for_display(
                display, self._band_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 200)
            self.win.connect('destroy', lambda *_: Gtk.StyleContext.remove_provider_for_display(
                display, self._band_provider))
        self._band_provider.load_from_string(css)

    def _no_path(self, cv):
        """In Recent (and searches) Nautilus shows the folder the file is in below
        the name: in the Explorer only the name."""
        for box in walk(cv):
            if not box.has_css_class('column-name-labels-box'):
                continue
            name = box.get_first_child()
            lbl = name.get_first_child() if isinstance(name, Gtk.Box) else None
            if isinstance(lbl, Gtk.Label) and lbl.get_ellipsize() != Pango.EllipsizeMode.END:
                # (cut at the end, as in XP; Nautilus cuts in the middle)
                lbl.set_ellipsize(Pango.EllipsizeMode.END)
            c = box.get_first_child()
            while c is not None:
                if isinstance(c, Gtk.Label) and c.has_css_class('caption'):
                    if not getattr(c, '_zxp_hidden', False):
                        c._zxp_hidden = True
                        # (Nautilus shows it again when recycling the cell)
                        c.connect('notify::visible', lambda l, _p: l.get_visible() and l.set_visible(False))
                    if c.get_visible():
                        c.set_visible(False)
                c = c.get_next_sibling()

    def _align_cells(self, cv):
        """Size right-aligned, as in XP (the cells are created and recycled by the
        list; the cells' order follows the columns')."""
        self._link_emblems(cv)
        self._no_path(cv)
        self._sel_cells(cv)
        cols = cv.get_columns()
        visible = [cols.get_item(i) for i in range(cols.get_n_items())
                   if cols.get_item(i).get_visible()]
        right = [i for i, c in enumerate(visible) if (c.get_id() or '') in RIGHT_ALIGNED]
        if not right:
            return False
        header = next((w for w in walk(cv) if w.get_css_name() == 'header'), None)
        if header:
            buttons = []
            b = header.get_first_child()
            while b:
                if b.get_visible():
                    buttons.append(b)
                b = b.get_next_sibling()
            for i in right:
                if i < len(buttons):
                    for w in walk(buttons[i]):
                        if w is buttons[i]:
                            continue
                        if w.get_parent() is buttons[i]:
                            w.set_halign(Gtk.Align.END)
                        if isinstance(w, Gtk.Label):
                            w.set_xalign(1)
        listview = next((w for w in walk(cv) if w.get_css_name() == 'listview'), None)
        row = listview.get_first_child() if listview else None
        while row:
            if row.get_css_name() == 'row':
                cells = []
                c = row.get_first_child()
                while c:
                    cells.append(c)
                    c = c.get_next_sibling()
                for i in right:
                    if i < len(cells):
                        for lbl in walk(cells[i]):
                            if isinstance(lbl, Gtk.Label) and lbl.get_xalign() != 1:
                                lbl.set_xalign(1)
            row = row.get_next_sibling()
        return False

    # ----------------------------- shortcuts of the special folders, without the arrow
    # "As minhas imagens", "A minha música"... inside "Os meus documentos" are
    # shortcuts (symbolic links): in XP they were the folders themselves, with
    # their icon (metadata, tools/setup/xpfolders.py) and without the shortcut
    # arrow, which Nautilus puts on every link — hidden here only on those.
    def _special_targets(self):
        if getattr(self, '_specials', None) is None:
            U = GLib.UserDirectory
            home = os.path.realpath(GLib.get_home_dir())
            self._specials = set()
            for d in (U.DIRECTORY_DOCUMENTS, U.DIRECTORY_PICTURES, U.DIRECTORY_MUSIC,
                      U.DIRECTORY_VIDEOS, U.DIRECTORY_DOWNLOAD, U.DIRECTORY_DESKTOP):
                path = GLib.get_user_special_dir(d)
                if path and os.path.realpath(path) != home:
                    self._specials.add(os.path.realpath(path))
        return self._specials

    def _is_special_link(self, uri):
        cache = self.__dict__.setdefault('_special_cache', {})
        if uri not in cache:
            special = False
            try:
                f = Gio.File.new_for_uri(uri)
                info = f.query_info('standard::is-symlink', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
                if info.get_is_symlink() and f.get_path():
                    special = os.path.realpath(f.get_path()) in self._special_targets()
            except GLib.Error:
                pass
            cache[uri] = special
        return cache[uri]

    def _link_emblems(self, root):
        for cell in walk(root):
            if cell.__gtype__.name not in ('NautilusGridCell', 'NautilusNameCell'):
                continue
            if not getattr(cell, '_zxp_links', False):
                cell._zxp_links = True
                # (cell recycled for another file: the emblems change afterwards)
                cell.connect('notify::item', lambda c, _p: GLib.timeout_add(
                    150, lambda: self._link_emblem(c)))
            self._link_emblem(cell)

    def _link_emblem(self, cell):
        item = cell.get_property('item')
        f = item.get_property('file') if item is not None else None
        special = False
        if f is not None:
            try:
                special = self._is_special_link(Nautilus.FileInfo.get_uri(f))
            except Exception:
                pass
        # the emblems box is hidden (Nautilus rebuilds the images inside it when
        # the file changes, but the box stays)
        box = getattr(cell, '_zxp_emblems', None)
        if box is None and cell.__gtype__.name == 'NautilusGridCell':
            # (in the grid: the column beside the icon)
            clamp = cell.get_first_child()
            vbox = clamp.get_first_child() if clamp else None
            icon_box = vbox.get_first_child() if vbox else None
            last = icon_box.get_last_child() if icon_box else None
            if last is not None and last is not icon_box.get_first_child():
                box = cell._zxp_emblems = last
        if box is None:
            for img in walk(cell):
                if isinstance(img, Gtk.Image) and img.get_ancestor(Gtk.MenuButton) is None:
                    g = img.get_gicon()
                    if isinstance(g, Gio.ThemedIcon) and any(n.startswith('emblem-symbolic-link')
                                                             for n in g.get_names()):
                        box = cell._zxp_emblems = img.get_parent()
                        break
        # (in Tiles, Thumbnails and Icons the emblems column always goes: in Tiles
        # it pushed the name away, in the others it took the icon off centre)
        grid_mode = getattr(self, '_mode', None) in PITCHES or getattr(self, '_mode', None) == 'list'
        hide = special or (grid_mode and cell.__gtype__.name == 'NautilusGridCell')
        if box is not None and box.get_visible() == hide:
            box.set_visible(not hide)
        return False

    def _tile_width_cb(self, scroller, grid):
        # (Gtk.Widget does not notify width changes: follow the window)
        for prop in ('notify::default-width', 'notify::default-height'):
            self.win.connect(prop, lambda *_: GLib.idle_add(lambda: self._tile_columns(grid) and False))
        self.win.connect('notify::maximized', lambda *_: GLib.timeout_add(
            200, lambda: self._tile_columns(grid) and False))

    def _tile_columns(self, grid):
        """Columns with XP's width (PITCHES): GtkGridView spreads the leftover
        among the columns; here the number of columns is fixed and the
        leftover stays on the right. List: the grid on its side (_list_rows)."""
        scroller = grid.get_parent()
        mode = getattr(self, '_mode', None)
        listing = mode == 'list'
        orient = Gtk.Orientation.HORIZONTAL if listing else Gtk.Orientation.VERTICAL
        if grid.get_orientation() != orient:
            grid.set_orientation(orient)
        # (only List scrolls sideways — and Details, Nautilus's list view)
        if isinstance(scroller, Gtk.ScrolledWindow):
            policy = (Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER) if listing else \
                (Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            if scroller.get_policy() != policy:
                scroller.set_policy(*policy)
        if listing and scroller:
            self._watch_list_model(grid)
            return self._list_rows(grid, scroller)
        grid.set_margin_bottom(0)
        pitch = PITCHES.get(mode)
        if pitch is None or not scroller:
            grid.set_min_columns(1)
            grid.set_max_columns(100)
            grid.set_margin_end(0)
            return False
        width = scroller.get_width() - 8   # grid padding (CSS)
        if width <= 0:
            return False
        n = max(1, width // pitch)
        grid.set_min_columns(n)
        grid.set_max_columns(n)
        grid.set_margin_end(max(0, width - n * pitch))
        return False

    def _list_rows(self, grid, scroller):
        """List: as many 17 px rows per column as fit in the view's height, less
        the horizontal scrollbar when the columns do not all fit (on its side,
        the grid's "columns" are its rows)."""
        avail = scroller.get_height()
        if avail <= 0:
            return False
        model = grid.get_model()
        n = model.get_n_items() if model is not None else 0
        rows = max(1, avail // LIST_ROW)
        if -(-n // rows) * self._list_width(grid) > scroller.get_width():
            bar = scroller.get_hscrollbar()
            avail -= bar.measure(Gtk.Orientation.VERTICAL, -1)[1] if bar else 0
            rows = max(1, avail // LIST_ROW)
        grid.set_min_columns(rows)
        grid.set_max_columns(rows)
        grid.set_margin_end(0)
        # (the leftover stays below the last row, as in XP: GtkGridView would
        # stretch the rows to fill the height)
        grid.set_margin_bottom(max(0, avail - rows * LIST_ROW))
        return False

    def _list_width(self, grid):
        """List: every column as wide as the folder's longest name (as in XP).
        Measured again for another folder, another number of items or a
        changed name (_watch_list_model)."""
        model = grid.get_model()
        slot = getattr(self, '_slot_obj', None)
        loc = slot.get_property('location') if slot else None
        key = (loc.get_uri() if loc else None, model.get_n_items() if model is not None else 0)
        cached = getattr(grid, '_zxp_list_w', None)
        if cached is not None and cached[0] == key:
            return cached[1]
        layout = grid.create_pango_layout('')
        widest = 0
        for i in range(model.get_n_items() if model is not None else 0):
            item = model.get_item(i)
            if isinstance(item, Gtk.TreeListRow):
                item = item.get_item()
            f = item.get_property('file') if item is not None else None
            if f is not None:
                layout.set_text(Nautilus.FileInfo.get_name(f), -1)
                widest = max(widest, layout.get_pixel_size()[0])
        width = LIST_TEXT_X + widest + LIST_GAP
        grid._zxp_list_w = (key, width)
        return width

    def _watch_list_model(self, grid):
        """A name added, removed or changed: List measures its columns again."""
        model = grid.get_model()
        if model is None or getattr(model, '_zxp_list_watch', False):
            return
        model._zxp_list_watch = True

        def changed(*_):
            grid._zxp_list_w = None
            if getattr(self, '_mode', None) == 'list' and not getattr(grid, '_zxp_list_idle', 0):
                def run():
                    grid._zxp_list_idle = 0
                    self._tile_columns(grid)
                    self._tile_cells(grid)
                    return False
                grid._zxp_list_idle = GLib.idle_add(run)
        model.connect('items-changed', changed)

    def _tile_cells(self, grid):
        on = getattr(self, '_tiles', False)
        listing = getattr(self, '_mode', None) == 'list'
        # (List and Tiles: the icon beside the name)
        side = on or listing
        list_w = self._list_width(grid) if listing else None
        # (a cell is redone when the view — or List's column width — changes)
        mark = (self._mode, list_w)
        for cell in walk(grid):
            if cell.__gtype__.name != 'NautilusGridCell' or \
                    getattr(cell, '_zxp_tile', None) == mark:
                continue
            clamp = cell.get_first_child()
            box = clamp.get_first_child() if clamp else None
            labels = box.get_last_child() if box else None
            if not isinstance(box, Gtk.Box) or not isinstance(labels, Gtk.Box):
                continue
            if not hasattr(cell, '_zxp_clamp'):
                cell._zxp_clamp = clamp.get_maximum_size()
            cell._zxp_tile = mark
            box.set_orientation(Gtk.Orientation.HORIZONTAL if side else Gtk.Orientation.VERTICAL)
            # (List: from the column's left edge; Nautilus centres the cell's content)
            if not hasattr(box, '_zxp_halign'):
                box._zxp_halign = (box.get_halign(), box.get_spacing())
            box.set_halign(Gtk.Align.START if listing else box._zxp_halign[0])
            # (and the name 18 px from the edge: without Nautilus's 6 px after the icon)
            box.set_spacing(0 if listing else box._zxp_halign[1])
            icon_box = box.get_first_child()
            if not hasattr(icon_box, '_zxp_halign'):
                icon_box._zxp_halign = icon_box.get_halign()
            icon_box.set_halign(Gtk.Align.START if side else icon_box._zxp_halign)
            if not hasattr(icon_box, '_zxp_hexpand'):
                icon_box._zxp_hexpand = icon_box.get_hexpand()
            icon_box.set_hexpand(False if side else icon_box._zxp_hexpand)
            icon_box.set_valign(Gtk.Align.CENTER if on else (Gtk.Align.START if listing else Gtk.Align.FILL))
            labels.set_valign(Gtk.Align.CENTER if side else Gtk.Align.FILL)
            labels.set_hexpand(side)
            clamp.set_maximum_size(TILE_WIDTH if on else (list_w if listing else cell._zxp_clamp))
            # (List: the whole column; above its tightening threshold the clamp gives
            # the content less than the width, centred)
            if not hasattr(cell, '_zxp_tight'):
                cell._zxp_tight = clamp.get_tightening_threshold()
            clamp.set_tightening_threshold(list_w if listing else cell._zxp_tight)
            # List: every cell as wide as the longest name, 17 px high (the grid on
            # its side gives each column the width of its widest cell)
            cell.set_size_request(list_w if listing else -1, LIST_ROW if listing else -1)
            # Icons and Thumbnails: the name in up to 2 lines, broken at spaces
            # and cut with "…" at the end (as in XP)
            two = self._mode in ('icons', 'thumbnails')
            for lbl in walk(labels):
                if isinstance(lbl, Gtk.Label):
                    if not hasattr(lbl, '_zxp_orig'):
                        lbl._zxp_orig = (lbl.get_wrap(), lbl.get_max_width_chars(),
                                         lbl.get_ellipsize(), lbl.get_lines(), lbl.get_wrap_mode())
                    wrap, chars, ell, lines, wrap_mode = lbl._zxp_orig
                    if two:
                        wrap, chars, ell, lines = False, -1, Pango.EllipsizeMode.NONE, -1
                    lbl.set_wrap_mode(wrap_mode)
                    lbl.set_xalign(0 if side else 0.5)
                    # the selection highlight only behind the text, as in XP
                    if not hasattr(lbl, '_zxp_halign'):
                        lbl._zxp_halign = lbl.get_halign()
                    lbl.set_halign(Gtk.Align.START if side else Gtk.Align.CENTER)
                    lbl.set_justify(Gtk.Justification.LEFT if side else Gtk.Justification.CENTER)
                    # one line per text: cut with "…" in Tiles (like XP's), whole in List
                    lbl.set_wrap(False if side else wrap)
                    lbl.set_lines(1 if side else lines)
                    lbl.set_max_width_chars(-1 if side else chars)
                    lbl.set_ellipsize(Pango.EllipsizeMode.END if on else (Pango.EllipsizeMode.NONE if listing else ell))
            name = labels.get_first_child()
            if isinstance(name, Gtk.Label):
                if not getattr(name, '_zxp_watch', False):
                    name._zxp_watch = True
                    name.add_css_class('zxp-name')
                    name.connect('notify::label', lambda l, _p: self._xp_name(l))
                    row = cell.get_parent()
                    if row is not None and row.get_css_name() == 'child':
                        name._zxp_row = row
                        row.connect('state-flags-changed', lambda _r, _f, l=name: self._xp_name(l))
                self._xp_name(name)
        self._link_emblems(grid)
        self._thumb_cells(grid)
        self._sel_cells(grid)
        return False

    def _xp_name(self, lbl):
        """The name as XP shows it in Icons and Thumbnails (DrawText with word
        breaking and "..." at the end): up to 2 lines broken at spaces; a word
        that does not fit on the first line is cut there, on its own; the
        second line takes the rest, cut at the end. Nautilus sets the whole
        name; the cut text goes on top (the real name in _zxp_name)."""
        text = lbl.get_label()
        if text != getattr(lbl, '_zxp_text', None):
            lbl._zxp_name = text        # (a name set by Nautilus)
        name = lbl._zxp_name
        width = NAME_WIDTHS.get(getattr(self, '_mode', None))
        # the selected item with the focus (the last one clicked) shows the whole
        # name while the view has the focus; every other name, long or short,
        # stays cut — also the focused one once it is no longer selected
        row = getattr(lbl, '_zxp_row', None)
        flags = row.get_state_flags() if row is not None else 0
        focused = bool(flags & Gtk.StateFlags.FOCUSED) and bool(flags & Gtk.StateFlags.SELECTED) and \
            self.win.is_active()

        def measure(t):
            return lbl.create_pango_layout(t).get_pixel_size()[0]
        # (the whole name goes on top of the rows below; the cell keeps the cut one,
        # so the grid never moves)
        self._name_on_top(lbl, xp_wrap(name, width, measure, None) if focused and width else None)
        key = (name, width)
        if key == getattr(lbl, '_zxp_key', None) and text == getattr(lbl, '_zxp_text', None):
            return
        lbl._zxp_key = key
        out = name if width is None else xp_wrap(name, width, measure, 2)
        lbl._zxp_text = out
        if out != text:
            lbl.set_label(out)

    def _name_on_top(self, lbl, full):
        """The whole name of the selected item (full; None: cut) goes over the
        rows below it without moving them, as in XP. In the cell it would
        make the row taller, and GtkGridView draws the following cells on top
        of it: it is a label in the view's overlay instead, centred on the
        cell's name and following it every frame; the cut name hides under it."""
        cur = getattr(self, '_name_over', None)
        if full is None:
            if cur is not None and cur[1] is lbl:
                self._drop_name_over()
            return
        if cur is not None and cur[1] is lbl:
            if cur[0].get_label() != full:
                cur[0].set_label(full)
            return
        self._drop_name_over()
        view = self._files_view()
        overlay = view.get_first_child() if view else None
        if not isinstance(overlay, Gtk.Overlay):
            return
        over = Gtk.Label(label=full, xalign=0.5, justify=Gtk.Justification.CENTER,
                         can_target=False, focusable=False, css_classes=['zxp-name-over'],
                         halign=Gtk.Align.START, valign=Gtk.Align.START, opacity=0)
        overlay.add_overlay(over)
        # (inside the files' area only: not over the view's scrollbar)
        overlay.set_clip_overlay(over, True)
        lbl.add_css_class('zxp-name-under')

        def follow(*_):
            ok, r = lbl.compute_bounds(overlay)
            # (hidden while the rename box is over the name, or the cell is gone)
            show = ok and lbl.get_mapped() and lbl.get_opacity() > 0
            if show:
                # (measure() counts the margins, which are the position given here)
                w = over.measure(Gtk.Orientation.HORIZONTAL, -1)[1] - \
                    over.get_margin_start() - over.get_margin_end()
                over.set_margin_start(max(0, math.floor(r.get_x() + r.get_width() / 2 - w / 2 + 0.5)))
                over.set_margin_top(max(0, int(r.get_y())))
            # (shown and hidden by opacity: a hidden widget gets no frame ticks)
            if (over.get_opacity() > 0) != show:
                over.set_opacity(1 if show else 0)
            return GLib.SOURCE_CONTINUE
        follow()
        self._name_over = (over, lbl, overlay, over.add_tick_callback(follow))

    def _drop_name_over(self):
        cur = getattr(self, '_name_over', None)
        if cur is None:
            return
        self._name_over = None
        over, lbl, overlay, tick = cur
        over.remove_tick_callback(tick)
        lbl.remove_css_class('zxp-name-under')
        if over.get_parent() is overlay:
            overlay.remove_overlay(over)

    # ------------------------------------------------------------ thumbnails
    # Thumbnails: XP's 96x96 frame (1 px #ECE9D8, white background), images
    # scaled down to fit inside (94x94), the others with the 48 px icon in
    # the centre (Nautilus stretched them to 96 and they got blurry). Icons:
    # 32 px (Nautilus has nothing below 48 in the grid). Icons and Tiles:
    # images with the type icon, as in XP. In all three, the icon in the
    # centre of the column, without the 18 px Nautilus leaves on the left to
    # balance the emblems column.
    def _thumb_cells(self, grid):
        mode = getattr(self, '_mode', None)
        on = mode == 'thumbnails'
        for cell in walk(grid):
            if cell.__gtype__.name != 'NautilusGridCell':
                continue
            pic = next((p for p in walk(cell) if isinstance(p, Gtk.Picture)), None)
            frame = pic.get_parent() if pic else None
            if frame is None:
                continue
            if not hasattr(pic, '_zxp_fit'):
                pic._zxp_fit = (pic.get_content_fit(), pic.get_valign())
                pic._zxp_cell = cell
                pic.connect('notify::paintable', lambda p, _x: self._thumb_picture(p))
            (frame.add_css_class if on else frame.remove_css_class)('zxp-thumb-frame')
            icon_box = frame.get_parent()
            if isinstance(icon_box, Gtk.Box):
                if not hasattr(icon_box, '_zxp_margin'):
                    icon_box._zxp_margin = icon_box.get_margin_start()
                flush = mode in ('thumbnails', 'icons', 'list')
                icon_box.set_margin_start(0 if flush else icon_box._zxp_margin)
                # Icons and List: 32x32 / 16x16 instead of the 48x48 Nautilus asks for;
                # leaving them, Nautilus's size for the new view's zoom (a size kept
                # from before could be the previous zoom's: Nautilus may set its own
                # after this runs)
                req = (icon_box.get_size_request().width, icon_box.get_size_request().height)
                small = SMALL_ICONS.get(mode)
                if small:
                    if req != (small, small):
                        icon_box._zxp_small = True
                        icon_box.set_size_request(small, small)
                elif getattr(icon_box, '_zxp_small', False):
                    icon_box._zxp_small = False
                    size = ZOOM_ICON_BOX.get(VIEW_MODES.get(mode, {}).get('zoom'))
                    if size and req != (size, size):
                        icon_box.set_size_request(size, size)
            self._thumb_picture(pic)

    def _thumb_picture(self, pic):
        """The cell's image for the current view, always from the one Nautilus
        set (_zxp_src): ours (_zxp_mine) and the selection one (_zxp_tex) do
        not count as its own."""
        mode = getattr(self, '_mode', None)
        on = mode == 'thumbnails'
        fit, valign = pic._zxp_fit
        pic.set_content_fit(Gtk.ContentFit.SCALE_DOWN if on else fit)
        pic.set_valign(Gtk.Align.CENTER if on else valign)
        cur = pic.get_paintable()
        if cur is None or cur == getattr(pic, '_zxp_tex', None):
            return
        mine = cur == getattr(pic, '_zxp_mine', None)
        if mine and getattr(pic, '_zxp_pmode', None) == mode:
            return
        if not mine:
            pic._zxp_src = cur
        pic._zxp_pmode = mode
        src = pic._zxp_src
        new = self._mode_paintable(pic, src, mode) or src
        pic._zxp_mine = None if new == src else new
        if new != cur:
            pic.set_paintable(new)

    def _mode_paintable(self, pic, src, mode):
        size = TYPE_ICON_SIZES.get(mode)
        if size is None:
            return src
        scale = pic.get_scale_factor()
        theme = Gtk.IconTheme.get_for_display(pic.get_display())
        if isinstance(src, Gtk.IconPaintable):
            width, name = src.get_intrinsic_width(), src.get_icon_name()
            if not name or width == size or (mode == 'thumbnails' and width < size):
                return src
            return theme.lookup_icon(name, None, size, scale, Gtk.TextDirection.NONE, 0)
        item = pic._zxp_cell.get_property('item')
        f = item.get_property('file') if item is not None else None
        if f is None:
            return src
        if mode == 'thumbnails':
            # a miniatura do Nautilus (cantos redondos, contorno): a do XP
            return self._xp_thumbnail(f) or src
        # a thumbnail in Icons or Tiles: the file type's icon
        mime = Nautilus.FileInfo.get_mime_type(f)
        if not mime:
            return src
        return theme.lookup_by_gicon(Gio.content_type_get_icon(mime), size, scale,
                                     Gtk.TextDirection.NONE, 0)

    def _xp_thumbnail(self, f):
        """The thumbnail as XP draws it in Thumbnails: the image scaled down to fit
        96x96 (small ones do not grow), centred; the 1 px grey frame is drawn
        over the edge (CSS outline) and, with the item selected, gives way to
        a 3 px blue one outside. It comes from the thumbnail file Nautilus
        already made."""
        try:
            info = Gio.File.new_for_uri(Nautilus.FileInfo.get_uri(f)).query_info(
                'thumbnail::path', Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error:
            return None
        path = info.get_attribute_byte_string('thumbnail::path')
        if not path:
            return None
        try:
            key = (path, os.stat(path).st_mtime)
        except OSError:
            return None
        cache = self.__dict__.setdefault('_thumb_cache', collections.OrderedDict())
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(path)
        except GLib.Error:
            return None
        w, h = pb.get_width(), pb.get_height()
        if w > 96 or h > 96:
            k = min(96 / w, 96 / h)
            w, h = max(1, round(w * k)), max(1, round(h * k))
            pb = pb.scale_simple(w, h, GdkPixbuf.InterpType.HYPER)
        tex = Gdk.Texture.new_for_pixbuf(pb)
        cache[key] = tex
        while len(cache) > 300:
            cache.popitem(last=False)
        return tex

    # ------------------------------------------------- selection as in XP
    # The icon of selected items is blended with the highlight colour
    # (HIGHLIGHT), pixel by pixel: Nautilus keeps showing its icon, here only
    # the Gtk.Picture's image is swapped while the item is selected and the
    # window active (inactive: the normal icon, as in XP).
    def _sel_cells(self, root):
        for cell in walk(root):
            if cell.__gtype__.name not in ('NautilusGridCell', 'NautilusNameCell'):
                continue
            pic = next((p for p in walk(cell) if isinstance(p, Gtk.Picture)), None)
            if pic is None or getattr(pic, '_zxp_sel', False):
                continue
            row = cell.get_parent()
            while row is not None and row.get_css_name() not in ('child', 'row'):
                row = row.get_parent()
            if row is None:
                continue
            pic._zxp_sel = True
            pic._zxp_row = row
            pic._zxp_orig = pic._zxp_tex = None
            pic._zxp_busy = False
            row.connect('state-flags-changed', lambda _r, _f, p=pic: self._sel_picture(p))
            pic.connect('notify::paintable', lambda p, _x: self._sel_picture(p))
            self._sel_picture(pic)
        if not getattr(self, '_sel_watch', False):
            self._sel_watch = True
            self.win.connect('notify::is-active', lambda *_: self._sel_all())
        # (the focus entering and leaving the view changes the selection, as in XP)
        view = root if isinstance(root, Gtk.GridView) else next(
            (w for w in walk(root) if w.get_css_name() == 'listview'), None)
        if view is not None and not getattr(view, '_zxp_focus', False):
            view._zxp_focus = True
            view._zxp_had = False

            def flags(v, _old):
                has = bool(v.get_state_flags() & Gtk.StateFlags.FOCUS_WITHIN)
                if has != v._zxp_had:
                    v._zxp_had = has
                    self._sel_all()
            view.connect('state-flags-changed', flags)

    def _sel_all(self):
        view = self._files_view()
        for w in walk(view) if view else ():
            if getattr(w, '_zxp_sel', False):
                self._sel_picture(w)
            elif getattr(w, '_zxp_row', None) is not None and isinstance(w, Gtk.Label):
                self._xp_name(w)        # (the whole name only with the window active)

    def _sel_picture(self, pic):
        if pic._zxp_busy:
            return
        cur = pic.get_paintable()
        if cur is None:
            return
        if pic._zxp_tex is None or cur != pic._zxp_tex:      # (a new icon from Nautilus)
            pic._zxp_orig, pic._zxp_tex = cur, None
        # (in Thumbnails XP does not tint the image: the frame turns blue, CSS;
        # without the focus on the view — typing a name, in the address — not either)
        view = pic._zxp_row.get_parent()
        focused = view is not None and bool(view.get_state_flags() & Gtk.StateFlags.FOCUS_WITHIN)
        want = bool(pic._zxp_row.get_state_flags() & Gtk.StateFlags.SELECTED) and focused and \
            self.win.is_active() and getattr(self, '_mode', None) != 'thumbnails'
        target = pic._zxp_orig
        if want:
            if pic._zxp_tex is None:
                pic._zxp_tex = self._blend(pic._zxp_orig, pic)
            target = pic._zxp_tex or pic._zxp_orig
        if cur != target:
            pic._zxp_busy = True
            pic.set_paintable(target)
            pic._zxp_busy = False

    def _blend(self, paintable, pic):
        """XP's selected image: pixels with alpha >= 128 halfway to the highlight
        colour, in premultiplied alpha (the result may exceed the alpha, as in
        XP: blending when drawing saturates)."""
        w, h = paintable.get_intrinsic_width(), paintable.get_intrinsic_height()
        if w <= 0 or h <= 0:
            return None
        # (at the image's own size — not the cell's, which may still be the
        # previous view's —, up to 128 px: big ones would be slow)
        f = min(1.0, 128 / w, 128 / h)
        w, h = max(1, round(w * f)), max(1, round(h * f))
        cache = self.__dict__.setdefault('_blend_cache', collections.OrderedDict())
        key = (paintable, w, h)
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        native = pic.get_native()
        renderer = native.get_renderer() if native else None
        snap = Gtk.Snapshot()
        paintable.snapshot(snap, w, h)
        node = snap.to_node()
        if renderer is None or node is None:
            return None
        rect = Graphene.Rect().init(0, 0, w, h)
        tex = renderer.render_texture(node, rect)
        down = Gdk.TextureDownloader.new(tex)
        down.set_format(Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED)
        data, stride = down.download_bytes()
        px = bytearray(data.get_data())
        r, g, b = HIGHLIGHT
        for i in range(3, len(px), 4):
            if px[i] >= 128:
                px[i - 3] = (px[i - 3] + b + 1) >> 1
                px[i - 2] = (px[i - 2] + g + 1) >> 1
                px[i - 1] = (px[i - 1] + r + 1) >> 1
        out = Gdk.MemoryTexture.new(tex.get_width(), tex.get_height(),
                                    Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
                                    GLib.Bytes.new(bytes(px)), stride)
        cache[key] = out
        while len(cache) > 300:
            cache.popitem(last=False)
        return out

    def _brand(self):
        """Windows flag in the corner of the menu bar; animates while loading."""
        self.brand = Gtk.Image(pixel_size=BRAND_SIZE, css_classes=['zxp-explorer-brand-flag'])
        self.brand_frames = []
        path = asset('explorer-brand')
        if path:
            strip = GdkPixbuf.Pixbuf.new_from_file(path)
            for i in range(strip.get_height() // BRAND_SIZE):
                sub = strip.new_subpixbuf(0, i * BRAND_SIZE, BRAND_SIZE, BRAND_SIZE)
                self.brand_frames.append(Gdk.Texture.new_for_pixbuf(sub))
            self.brand.set_from_paintable(self.brand_frames[0])
        self.brand_timer = 0
        box = Gtk.Box(css_classes=['zxp-explorer-brand'])
        box.append(self.brand)
        return box

    def _animate_brand(self, on):
        if not self.brand_frames:
            return
        if on and not self.brand_timer:
            self.brand_i = 0

            def step():
                self.brand_i = (self.brand_i + 1) % len(self.brand_frames)
                self.brand.set_from_paintable(self.brand_frames[self.brand_i])
                return GLib.SOURCE_CONTINUE
            self.brand_timer = GLib.timeout_add(BRAND_FRAME_MS, step)
        elif not on and self.brand_timer:
            GLib.source_remove(self.brand_timer)
            self.brand_timer = 0
            self.brand.set_from_paintable(self.brand_frames[0])

    def _tool(self, key, icon, action, label=True, toggle=False, dropdown=False):
        btn = (Gtk.ToggleButton if toggle else Gtk.Button)(
            css_classes=['zxp-explorer-tool', 'flat', f'zxp-tool-{key}'], focusable=False)
        box = Gtk.Box(spacing=4)
        img = image(f'explorer-{key}-normal', icon)
        box.append(img)
        if label:
            box.append(Gtk.Label(label=T[key]))
        arrow = None
        if dropdown:
            arrow = Gtk.Image(css_classes=['zxp-dropdown', dropdown], valign=Gtk.Align.CENTER)
            box.append(arrow)
        btn.set_child(box)
        btn.set_tooltip_text(T[key])
        if action:
            btn.set_action_name(action)

        # "hot" image on hover and grey when disabled
        def sync(*_):
            state = 'disabled' if not btn.get_sensitive() else (
                'hot' if btn.get_state_flags() & Gtk.StateFlags.PRELIGHT else 'normal')
            path = asset(f'explorer-{key}-{state}')
            if path and getattr(img, '_zxp', None) != path:
                img.set_from_file(path)
                img._zxp = path
            if arrow:
                apath = asset('explorer-dropdown-' + ('disabled' if state == 'disabled' else 'normal'))
                if apath and getattr(arrow, '_zxp', None) != apath:
                    arrow.set_from_file(apath)
                    arrow._zxp = apath
        btn.connect('state-flags-changed', sync)
        btn.connect('notify::sensitive', sync)
        sync()
        return btn

    def _toolbar(self):
        bar = Gtk.Box(css_classes=['zxp-explorer-toolbar'])
        for key, icon, action, label, drop in (('back', 'go-previous', 'win.back', True, 'split'),
                                               ('forward', 'go-next', 'win.forward', False, 'split'),
                                               ('up', 'go-up', 'win.up', False, None)):
            bar.append(self._tool(key, icon, action, label, dropdown=drop))
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.search_btn = self._tool('search', 'edit-find', None, True, toggle=True)
        self.search_btn.connect('toggled', self._on_search)
        bar.append(self.search_btn)
        bar.append(self._tool('folders', 'folder', 'xp.toggle-folders', True))
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        views = self._tool('views', 'view-grid', None, False, dropdown='attached')
        pop = Gtk.PopoverMenu.new_from_model(self._views_menu())
        pop.set_has_arrow(False)
        pop.set_position(Gtk.PositionType.BOTTOM)
        pop.set_halign(Gtk.Align.START)
        pop.set_parent(views)
        views.connect('clicked', lambda *_: pop.popup())
        bar.append(views)
        return bar

    def _addressbar(self):
        bar = Gtk.Box(spacing=4, css_classes=['zxp-explorer-address'])
        bar.append(Gtk.Label(label=T['address'], css_classes=['dim-label']))
        self.entry = Gtk.Entry(hexpand=True)
        self.entry.connect('activate', lambda *_: self._go())
        # drop-down button inside the box, as in XP's address bar
        arrow = asset('combo-arrow-normal')
        if arrow:
            self.entry.set_icon_from_paintable(Gtk.EntryIconPosition.SECONDARY,
                                               Gdk.Texture.new_from_filename(arrow))
            self.entry.connect('icon-press', lambda e, _pos: (e.grab_focus(), e.select_region(0, -1)))
        bar.append(self.entry)
        go = Gtk.Button(css_classes=['zxp-explorer-go', 'flat'], focusable=False)
        box = Gtk.Box(spacing=4)
        box.append(image('explorer-go-normal', 'go-next', 20))
        box.append(Gtk.Label(label=T['go']))
        go.set_child(box)
        go.set_action_name('xp.go')
        bar.append(go)
        return bar

    def _section(self, title, body, special=None):
        """An XP task pane section: header (shellstyle.dll bitmap 112, bold blue
        title, 21×23 collapse arrow) and body. The special ones (Music,
        Pictures, Videos) have the blue header (110), the 32 px icon sticking
        out on top and a watermark in the body."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=['zxp-taskpane-section'])
        header = Gtk.Button(css_classes=['zxp-taskpane-header'], focusable=False)
        prefix = 'explorer-section'
        if special:
            header.add_css_class('special')
            body.add_css_class('special')
            body.add_css_class(f'zxp-wm-{special}')
            prefix = 'explorer-special'
        hbox = Gtk.Box()
        label = Gtk.Label(label=title, hexpand=True, xalign=0)
        hbox.append(label)
        arrow = Gtk.Image(pixel_size=23, css_classes=['zxp-taskpane-arrow'])
        hbox.append(arrow)
        header.set_child(hbox)
        body.add_css_class('zxp-taskpane-body')

        def sync(*_):
            hot = '-hot' if header.get_state_flags() & Gtk.StateFlags.PRELIGHT else ''
            path = asset(prefix + ('-collapse' if body.get_visible() else '-expand') + hot)
            if path and getattr(arrow, '_zxp', None) != path:
                arrow.set_from_file(path)
                arrow._zxp = path
        header.connect('clicked', lambda *_: (body.set_visible(not body.get_visible()), sync()))
        header.connect('state-flags-changed', sync)
        sync()
        box.append(header)
        box.append(body)
        box._zxp_label = label
        if not special:
            return box
        overlay = Gtk.Overlay(child=box)
        icon = Gtk.Image(pixel_size=32, halign=Gtk.Align.START, valign=Gtk.Align.START,
                         can_target=False, css_classes=['zxp-special-icon'])
        path = asset(f'explorer-{special}-icon')
        if path:
            icon.set_from_file(path)
        overlay.add_overlay(icon)
        overlay._zxp_label = label
        return overlay

    def _task(self, icon, text, action):
        btn = Gtk.Button(css_classes=['zxp-task', 'flat'], focusable=False)
        box = Gtk.Box(spacing=6)
        img = Gtk.Image(pixel_size=16)
        path = asset(f'explorer-task-{icon}')
        if path:
            img.set_from_file(path)
        box.append(img)
        box.append(Gtk.Label(label=text, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, hexpand=True))
        btn.set_child(box)
        if action:
            btn.connect('clicked', lambda *_: self._view_action(action))
        return btn

    def _view_action(self, action):
        if action == 'new-folder':
            return self._new_folder()
        if action == 'rename':
            return self._rename_selected()
        if action == 'move-to-trash':
            return self._confirm_delete()
        view = self._files_view()
        if view:
            view.activate_action(f'view.{action}', None)

    # ------------------------------------------ new folder and rename
    # As in XP: the folder is created at once ("Nova pasta", "Nova pasta
    # (2)"…) and the name goes into an edit box over the item, instead of
    # Nautilus's windows; Enter or clicking outside confirms, Esc cancels.
    def _keys(self, _ctrl, keyval, _code, state):
        mods = state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK |
                        Gdk.ModifierType.ALT_MASK)
        if getattr(self, '_editor', None):
            return False
        if mods == Gdk.ModifierType.CONTROL_MASK and keyval in (
                Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_minus, Gdk.KEY_0, Gdk.KEY_KP_Add,
                Gdk.KEY_KP_Subtract, Gdk.KEY_KP_0):
            return True                     # (no zoom)
        if keyval == Gdk.KEY_F2 and not mods:
            return self._rename_selected()
        if keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete) and mods in (0, Gdk.ModifierType.SHIFT_MASK):
            # (only with the focus on the files: in the address Delete deletes
            # letters; Shift+Delete deletes permanently, as in XP)
            focus, view = self.win.get_focus(), self._files_view()
            if focus is not None and view is not None and focus.is_ancestor(view) and self._selection():
                self._confirm_delete(permanent=bool(mods))
                return True
        if keyval in (Gdk.KEY_N, Gdk.KEY_n) and mods == (Gdk.ModifierType.CONTROL_MASK |
                                                         Gdk.ModifierType.SHIFT_MASK):
            self._new_folder()
            return True
        return False

    def _new_folder(self):
        slot = getattr(self, '_slot_obj', None)
        loc = slot.get_property('location') if slot else None
        if loc is None or loc.get_path() is None:
            return self._nautilus_view_action('new-folder')
        base = T['new-folder-name']
        name, n = base, 1
        while loc.get_child(name).query_exists(None):
            n += 1
            name = f'{base} ({n})'
        target = loc.get_child(name)
        try:
            target.make_directory(None)
        except GLib.Error:
            return self._nautilus_view_action('new-folder')
        self._edit_when_shown(target)

    def _new_toplevels(self, model, pos, _removed, added):
        for i in range(pos, pos + added):
            dlg = model.get_item(i)
            if dlg.__gtype__.name == 'GtkMessageDialog' and \
                    GLib.get_monotonic_time() < getattr(self, '_auto_delete_until', 0):
                # Nautilus's question after ours (_delete_now): "Delete"
                self._auto_delete_until = 0
                dlg.set_opacity(0)

                def confirm(d=dlg):
                    b = next((w for w in walk(d) if isinstance(w, Gtk.Button) and
                              w.has_css_class('destructive-action')), None)
                    if b is not None:
                        b.emit('clicked')
                    return False
                GLib.idle_add(confirm)
                continue
            if dlg.__gtype__.name == 'NautilusNewFolderDialog':
                def swap(d=dlg):
                    if d.get_transient_for() == self.win:
                        d.close()
                        self._new_folder()
                    return False
                GLib.idle_add(swap)

    # ------------------------------------------------- eliminar, como no XP
    def _confirm_delete(self, permanent=False):
        """XP's question before deleting (texts and layout of shell32 dialogs
        1011-1013): to the Recycle Bin, with the sound afterwards; permanently
        (Shift+Delete, or already inside the Recycle Bin), without sound."""
        files = self._selection()
        if not files:
            return False
        if self._location_scheme() == 'trash':
            permanent = True
        kind = 'kill' if permanent else 'ask'
        if len(files) == 1:
            f = files[0]
            name = Nautilus.FileInfo.get_name(f)
            folder = Nautilus.FileInfo.is_directory(f)
            title = T['confirm-folder' if folder else 'confirm-file']
            text = T[f'{kind}-folder' if folder else f'{kind}-file'].format(name)
            icon = 'confirm-folder' if folder else 'confirm-file'
        else:
            title, text, icon = T['confirm-many'], T[f'{kind}-many'].format(len(files)), 'confirm-many'
        if not permanent:
            # the Recycle Bin's icon as it is (empty or full), as in XP
            try:
                count = Gio.File.new_for_uri('trash:///').query_info(
                    'trash::item-count', Gio.FileQueryInfoFlags.NONE, None).get_attribute_uint32(
                    'trash::item-count')
            except GLib.Error:
                count = 0
            icon = 'bin-full' if count else 'bin-empty'
        uris = [Nautilus.FileInfo.get_uri(f) for f in files]

        def yes():
            if permanent:
                self._delete_now(uris)
                return
            view = self._files_view()
            if view is not None:
                view.activate_action('view.move-to-trash', None)
                play_sound(TRASH_SOUND)
        self._xp_message(title, text, icon, yes, many=len(files) > 1)
        return True

    def _delete_now(self, uris):
        """Delete permanently through Nautilus's own operations (progress,
        errors); its question, which comes next, has already been asked the XP
        way: it is answered here without ever showing (_new_toplevels)."""
        self._auto_delete_until = GLib.get_monotonic_time() + 5 * 1000000

        def got(_o, res):
            try:
                proxy = Gio.DBusProxy.new_for_bus_finish(res)
            except GLib.Error as e:
                print(f'Zorin XP: eliminar: {e}')
                return
            # (asynchronous: the call is to the process itself)
            proxy.call('DeleteURIs', GLib.Variant('(asa{sv})', (uris, {})), Gio.DBusCallFlags.NONE,
                       -1, None, lambda p, r: p.call_finish(r))
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None, 'org.gnome.Nautilus',
                                  '/org/gnome/Nautilus/FileOperations2', 'org.gnome.Nautilus.FileOperations2',
                                  None, got)

    def _xp_message(self, title, text, icon, on_yes, many=False):
        """An XP message box (Yes / No), sized like shell32's confirmation dialog
        (Tahoma 8 dialog units = 1.5 px): 412 x 127 px (several items:
        412 x 97), the 32 px icon at (15, 15), the text beside it, the buttons
        at the bottom right."""
        dlg = Gtk.Window(title=title, transient_for=self.win, modal=True, resizable=False,
                         css_classes=['zxp-message'])
        fixed = Gtk.Fixed()
        fixed.set_size_request(412, 97 if many else 127)
        img = Gtk.Image(pixel_size=32)
        path = asset(f'explorer-{icon}')
        if path:
            img.set_from_file(path)
        fixed.put(img, 15, 15)
        # (the text broken here, at the dialog's width: a wrapping label asks the
        # Gtk.Fixed for the height of a 1-letter-wide column)
        label = Gtk.Label(xalign=0, yalign=0)
        width = 336 if many else 330

        def measure(t):
            return label.create_pango_layout(t).get_pixel_size()[0]
        label.set_label('\n'.join(xp_wrap(par, width, measure, None) if par else ''
                                  for par in text.split('\n')))
        fixed.put(label, 62 if many else 57, 21 if many else 15)
        answered = []

        def answer(ok):
            if answered:
                return
            answered.append(ok)
            dlg.close()
            if ok:
                on_yes()
        buttons = ((T['yes'], 220, True), (T['no'], 315, False)) if many else \
            ((T['yes'], 236, True), (T['no'], 322, False))
        default = None
        for text_, x, ok in buttons:
            b = Gtk.Button(label=text_, use_underline=True)
            b.set_size_request(87 if many else 80, 23)
            b.connect('clicked', lambda _b, ok=ok: answer(ok))
            fixed.put(b, x, 63 if many else 93)
            if ok:
                default = b
        dlg.set_child(fixed)
        dlg.set_default_widget(default)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', lambda _c, kv, *_: (answer(False), True)[1]
                     if kv == Gdk.KEY_Escape else False)
        dlg.add_controller(keys)
        dlg.present()
        default.grab_focus()

    def _nautilus_view_action(self, action):
        view = self._files_view()
        if view:
            view.activate_action(f'view.{action}', None)

    def _rename_selected(self):
        sel = self._selection()
        if len(sel) != 1:
            return False
        try:
            target = Gio.File.new_for_uri(Nautilus.FileInfo.get_uri(sel[0]))
        except Exception:
            return False
        return self._start_edit(target)

    def _edit_when_shown(self, target, tries=30):
        """Waits for the new item to appear in the view, selects it and edits it."""
        def attempt():
            nonlocal tries
            tries -= 1
            if self._select(target) and self._start_edit(target):
                return False
            return tries > 0
        GLib.timeout_add(100, attempt)

    def _select(self, target):
        view = self._files_view()
        widget = (find(view, 'GtkGridView') or find(view, 'GtkColumnView')) if view else None
        model = widget.get_model() if widget else None
        if model is None:
            return False
        uri = target.get_uri()
        for pos in range(model.get_n_items()):
            item = model.get_item(pos)
            if isinstance(item, Gtk.TreeListRow):
                item = item.get_item()
            f = item.get_property('file') if item is not None else None
            if f is not None and Nautilus.FileInfo.get_uri(f) == uri:
                flags = Gtk.ListScrollFlags.SELECT | Gtk.ListScrollFlags.FOCUS
                if isinstance(widget, Gtk.ColumnView):
                    widget.scroll_to(pos, None, flags, None)
                else:
                    widget.scroll_to(pos, flags, None)
                return True
        return False

    def _start_edit(self, target):
        # (one edit at a time: the open one is confirmed)
        if getattr(self, '_editor', None) is not None and getattr(self, '_editor_finish', None):
            self._editor_finish(True)
        view = self._files_view()
        overlay = view.get_first_child() if view else None
        if not isinstance(overlay, Gtk.Overlay):
            return False
        try:
            name = target.query_info('standard::display-name,standard::type',
                                     Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error:
            return False
        display = name.get_display_name()
        is_dir = name.get_file_type() == Gio.FileType.DIRECTORY
        # a etiqueta do nome desse item na vista
        label = None
        for w in walk(view):
            if isinstance(w, Gtk.Label) and getattr(w, '_zxp_name', w.get_label()) == display and \
                    w.get_mapped() and \
                    not w.has_css_class('caption') and not w.has_css_class('numeric'):
                label = w
                break
        if label is None:
            return False
        ok, rect = label.compute_bounds(overlay)
        if not ok:
            return False
        # the box as in XP (measured): the text stays where the name was; with the
        # name centred (Icons, Thumbnails) the box is centred on the item (see
        # EDIT_TEXT_W); on the left (Tiles) 4 px before and 15 after; in List and
        # Details 2 px before (so it does not touch the icon) and 15 after.
        # 17 px high: the text (13) + 1 px + the outline, above and below.
        mode = getattr(self, '_mode', None)
        # (List is the grid on its side, but its box is the one of Nautilus's list:
        # the whole 17 px row, 2 px before the name)
        grid = label.get_ancestor(Gtk.GridView) is not None and mode != 'list'
        centred = grid and mode in ('icons', 'thumbnails')
        kind = 'zxp-rename-left' if grid and not centred else ('zxp-rename-list' if not grid else '')
        before, after = (EDIT_PAD, EDIT_PAD) if centred else ((4, 15) if grid else (2, 15))
        if centred:
            # (always a box that can take more lines: the name may outgrow one line
            # while typing; inside a frame with the size calculated here, because a
            # wrapping text asks for the height of a 1-letter-wide column and for
            # the width of its last layout — EXTERNAL keeps both out of the frame's size)
            editor = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, justification=Gtk.Justification.CENTER,
                                  accepts_tab=False)
            entry = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.EXTERNAL,
                                       vscrollbar_policy=Gtk.PolicyType.EXTERNAL, child=editor,
                                       css_classes=['zxp-rename', 'zxp-rename-multi'],
                                       halign=Gtk.Align.START, valign=Gtk.Align.START)
            buf = editor.get_buffer()
            buf.set_text(display)

            def get_text():
                return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        else:
            entry = editor = Gtk.Entry(text=display, css_classes=['zxp-rename'] + ([kind] if kind else []),
                                       halign=Gtk.Align.START, valign=Gtk.Align.START,
                                       width_chars=1, max_width_chars=1)
            get_text = entry.get_text
        multi = centred
        size = [0, 17]

        def place():
            # (a new item's cell still moves for a few moments, and the view may
            # scroll: the box follows the name while typing)
            ok, rect = label.compute_bounds(overlay)
            if not ok:
                return
            pad = label.get_style_context().get_padding()
            shown_w = label.get_layout().get_pixel_size()[0]
            if centred:
                # (on the centre of the item's name; XP rounds the half pixel up)
                centre = rect.get_x() + pad.left + (rect.get_width() - pad.left - pad.right) / 2
                x = math.floor(centre - size[0] / 2 + 0.5)
            else:
                x = int(round(rect.get_x() + pad.left + label.get_xalign() *
                              (rect.get_width() - pad.left - pad.right - shown_w))) - before - 1
            if grid:
                # (in Thumbnails right below the selection's 3 px frame)
                y = int(rect.get_y()) + pad.top - 2 + (1 if mode == 'thumbnails' else 0)
            else:
                # (in List and Details the box takes the row: 17 px)
                row = label.get_parent()
                while row is not None and row.get_css_name() not in ('row', 'child'):
                    row = row.get_parent()
                ok_row, rrect = row.compute_bounds(overlay) if row is not None else (False, None)
                y = int(rrect.get_y()) if ok_row else int(rect.get_y()) - 1
            entry.set_margin_start(max(0, x))
            entry.set_margin_top(max(0, y))

        def grow(*_):
            # grows with the typed text: centred, on both sides while it fits on
            # one line, then downwards with more lines (as in XP)
            layout = editor.create_pango_layout(get_text())
            w = layout.get_pixel_size()[0]
            if centred and w > EDIT_TEXT_W:
                layout.set_width(EDIT_TEXT_W * Pango.SCALE)
                layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                size[:] = [EDIT_TEXT_W + before + after + 2, 4 + EDIT_LINE * layout.get_line_count()]
            else:
                size[:] = [w + before + after + 2, 17]
            entry.set_size_request(*size)
            place()
        grow()
        (buf if multi else entry).connect('changed', grow)

        def follow():
            if getattr(self, '_editor', None) is None or self._editor[0] is not entry:
                return False
            place()
            return True
        GLib.timeout_add(50, follow)
        overlay.add_overlay(entry)
        label.set_opacity(0)
        self._editor = (entry, label, overlay, target, display)

        def finish(commit):
            if getattr(self, '_editor', None) is None or self._editor[0] is not entry:
                return
            self._editor = None
            new = get_text().replace('\n', ' ').strip()
            label.set_opacity(1)
            overlay.remove_overlay(entry)
            if view:
                view.grab_focus()
            if not (commit and new and new != display):
                return

            def rename():
                try:
                    target.set_display_name(new, None)
                except GLib.Error as e:
                    print(f'Zorin XP: mudar o nome: {e}')
            # extension changed: XP's question (shell32, string 4112)
            if not is_dir and os.path.splitext(display)[1].lower() != os.path.splitext(new)[1].lower():
                self._xp_message(T['rename'], T['ask-extension'], 'warning', rename)
            else:
                rename()

        if not multi:
            entry.connect('activate', lambda *_: finish(True))
        self._editor_finish = finish
        keys = Gtk.EventControllerKey()

        def key(_c, kv, *_):
            if kv == Gdk.KEY_Escape:
                finish(False)
                return True
            if multi and kv in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                finish(True)            # (Enter confirms, it does not add a line)
                return True
            return False
        keys.connect('key-pressed', key)
        editor.add_controller(keys)
        focus = Gtk.EventControllerFocus()
        started = GLib.get_monotonic_time()

        def left(*_):
            # (right when it opens, the focus may be given back elsewhere — when
            # Nautilus's popover closes, for example: the box takes it back)
            if GLib.get_monotonic_time() - started < 400000:
                GLib.idle_add(lambda: editor.grab_focus() and False)
                return
            GLib.idle_add(lambda: finish(True) and False)
        focus.connect('leave', left)
        editor.add_controller(focus)
        editor.grab_focus()
        # name without the extension selected (as in XP); folders: everything
        dot = display.rfind('.')
        end = dot if (not is_dir and dot > 0) else len(display)
        if multi:
            buf.select_range(buf.get_start_iter(), buf.get_iter_at_offset(end))
        else:
            entry.select_region(0, end)
        return True

    def _task_pane(self):
        places = find(self.sidebar_tv, 'NautilusGtkPlacesSidebar')
        if not places or not isinstance(self.sidebar_tv, Adw.ToolbarView):
            return
        self.sidebar_tv.add_css_class('zxp-taskpane')
        # XP's task pane: 250 px
        self.split.set_min_sidebar_width(250)
        self.split.set_max_sidebar_width(250)

        # Nautilus's places go into a section ("Outros locais"), only as tall as
        # the items; the whole pane scrolls, as in XP
        self.sidebar_tv.set_content(None)
        inner = find(places, 'GtkScrolledWindow')
        if inner:
            inner.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
            inner.set_propagate_natural_height(True)
        places.set_vexpand(False)

        self.tasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tasks_section = self._section(T['file-tasks'], self.tasks_box)
        sections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=['zxp-taskpane-sections'])
        # the folder's special section (Music, Pictures, Videos), on top
        self.special_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.special_kind = None
        sections.append(self.special_slot)
        sections.append(self.tasks_section)
        sections.append(self._section(T['other-places'], places))
        # the shortcuts (bookmarks) separately, only when there are any
        self.shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.shortcuts_section = self._section(T['shortcuts'], self.shortcuts_box)
        sections.append(self.shortcuts_section)
        sections.append(self._section(T['details'], self.details_box))
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
                                      css_classes=['zxp-taskpane-scroller'])
        scroller.set_child(sections)
        self.sidebar_tv.set_content(scroller)

        # colour icons (Nautilus uses the monochrome symbolic ones)
        listbox = find(places, 'GtkListBox')
        self._places = places
        self._places_list(listbox)
        self._watch_shortcuts()

        pending = [0]

        def soon(*_):
            # (one pass per cycle, however many notices arrive)
            if not pending[0]:
                pending[0] = GLib.idle_add(color_icons)

        def color_icons(*_):
            pending[0] = 0
            for img in walk(listbox):
                if not isinstance(img, Gtk.Image):
                    continue
                g = img.get_gicon()
                if isinstance(g, Gio.ThemedIcon):
                    names = [n[:-len('-symbolic')] for n in g.get_names() if n.endswith('-symbolic')]
                    # Recent and Favorites with XP's icons (the Start menu's "Documentos
                    # recentes" and "Favoritos")
                    names = [SIDEBAR_ICONS.get(n, n) for n in names]
                    icon = Gio.ThemedIcon.new_from_names(names) if names else None
                    # only if it changes: swapping the icon emits notify::gicon, which would
                    # come back here endlessly (Nautilus got stuck)
                    if icon is not None and not g.equal(icon):
                        img.set_from_gicon(icon)
                if img.get_pixel_size() != 16:
                    img.set_pixel_size(16)
                if not getattr(img, '_zxp_watch', False):
                    img._zxp_watch = True
                    img.connect('notify::gicon', soon)
            return False
        if listbox:
            # (the model must stay stored, otherwise it stops notifying)
            listbox._zxp_children = listbox.observe_children()
            listbox._zxp_children.connect('items-changed', soon)
            color_icons()
        self._sync_details()

    # ------------------------------------------ "Outros locais" e "Atalhos"
    def _places_list(self, listbox):
        """Other Places only with O meu computador, Os meus documentos, Recent,
        Favorites and Downloads, in this order (and the pens/disks plugged in
        at the end, while they are there); without the separator lines."""
        if listbox is None:
            return
        U = GLib.UserDirectory

        def uri(path):
            return Gio.File.new_for_path(path).get_uri() if path else None
        where = {'home': uri(GLib.get_home_dir()),
                 'documents': uri(GLib.get_user_special_dir(U.DIRECTORY_DOCUMENTS)),
                 'recent': 'recent:///', 'starred': 'starred:///',
                 'downloads': uri(GLib.get_user_special_dir(U.DIRECTORY_DOWNLOAD))}
        ranks = {}
        for i, key in enumerate(OTHER_PLACES):
            if where[key] and where[key] not in ranks:
                ranks[where[key]] = i

        def rank(row):
            if row.__gtype__.name != 'NautilusGtkSidebarRow':
                return None
            r = ranks.get(row.get_property('uri') or '')
            if r is None and int(row.get_property('section-type')) == SECTION_MOUNTS:
                r = 100
            return r

        def order(a, b):
            ra, rb = rank(a), rank(b)
            return (1000 if ra is None else ra) - (1000 if rb is None else rb)
        listbox.set_filter_func(lambda row: rank(row) is not None)
        listbox.set_sort_func(order)
        listbox.set_header_func(None)

    def _open_place(self, uri):
        # (like a click on the places: opens in this window)
        places = getattr(self, '_places', None)
        if places is not None:
            places.emit('open-location', Gio.File.new_for_uri(uri), OPEN_NORMAL)

    def _not_shortcuts(self):
        """What does not go into the Shortcuts: the home folder and the XDG ones
        (xdg-user-dirs puts them in the bookmarks; they are in Other Places or
        inside Os meus documentos)."""
        U = GLib.UserDirectory
        out = {Gio.File.new_for_path(GLib.get_home_dir()).get_uri()}
        for d in (U.DIRECTORY_DESKTOP, U.DIRECTORY_DOCUMENTS, U.DIRECTORY_DOWNLOAD,
                  U.DIRECTORY_MUSIC, U.DIRECTORY_PICTURES, U.DIRECTORY_PUBLIC_SHARE,
                  U.DIRECTORY_TEMPLATES, U.DIRECTORY_VIDEOS):
            path = GLib.get_user_special_dir(d)
            if path:
                out.add(Gio.File.new_for_path(path).get_uri())
        return out

    @staticmethod
    def _bookmark_lines():
        try:
            with open(BOOKMARKS, encoding='utf-8') as f:
                return f.read().splitlines()
        except OSError:
            return []

    @staticmethod
    def _same_uri(uri):
        # (bookmarks may write the same address another way)
        return Gio.File.new_for_uri(uri).get_uri()

    def _shortcuts(self):
        """[(address, name)]: GTK's bookmarks (the same as Nautilus's sidebar and
        the open/save dialogs'), minus the home folders."""
        skip = self._not_shortcuts()
        out = []
        for line in self._bookmark_lines():
            uri, _sep, label = line.partition(' ')
            if uri and self._same_uri(uri) not in skip:
                out.append((uri, label.strip()))
        return out

    def _can_shortcut(self, uri):
        scheme = Gio.File.new_for_uri(uri).get_uri_scheme() or ''
        return scheme not in ('recent', 'starred', 'trash', 'other-locations', 'x-nautilus-search',
                              'network', 'computer', 'burn', 'admin') and \
            self._same_uri(uri) not in self._not_shortcuts()

    def _is_shortcut(self, uri):
        uri = self._same_uri(uri)
        return any(self._same_uri(u) == uri for u, _l in self._shortcuts())

    def _write_bookmarks(self, lines):
        os.makedirs(os.path.dirname(BOOKMARKS), exist_ok=True)
        GLib.file_set_contents(BOOKMARKS, ''.join(l + '\n' for l in lines).encode('utf-8'))

    def _add_shortcut(self, uri):
        if self._can_shortcut(uri) and not self._is_shortcut(uri):
            self._write_bookmarks(self._bookmark_lines() + [uri])
        self._sync_shortcuts()

    def _remove_shortcut(self, uri):
        uri = self._same_uri(uri)
        self._write_bookmarks([l for l in self._bookmark_lines()
                               if not l.strip() or self._same_uri(l.partition(' ')[0]) != uri])
        self._sync_shortcuts()

    def _watch_shortcuts(self):
        # (Nautilus and the open dialogs also change the bookmarks)
        self._bookmarks_monitor = Gio.File.new_for_path(BOOKMARKS).monitor_file(
            Gio.FileMonitorFlags.NONE, None)
        self._shortcuts_idle = 0

        def soon(*_):
            if not self._shortcuts_idle:
                self._shortcuts_idle = GLib.idle_add(self._sync_shortcuts)
        self._bookmarks_monitor.connect('changed', soon)
        self._sync_shortcuts()

    def _sync_shortcuts(self):
        self._shortcuts_idle = 0
        box = self.shortcuts_box
        items = self._shortcuts()
        key = tuple(items)
        if getattr(box, '_zxp_items', None) != key:
            box._zxp_items = key
            while box.get_first_child() is not None:
                box.remove(box.get_first_child())
            for uri, label in items:
                box.append(self._shortcut_button(uri, label))
        self.shortcuts_section.set_visible(bool(items))
        return False

    def _shortcut_button(self, uri, label):
        f = Gio.File.new_for_uri(uri)
        btn = Gtk.Button(css_classes=['zxp-task', 'flat'], focusable=False)
        row = Gtk.Box(spacing=6)
        img = Gtk.Image(pixel_size=16, icon_name='folder')
        name = Gtk.Label(label=label or f.get_basename() or uri, xalign=0, wrap=True,
                         wrap_mode=Pango.WrapMode.WORD_CHAR, hexpand=True)
        row.append(img)
        row.append(name)
        btn.set_child(row)
        btn.set_tooltip_text(f.get_parse_name())

        def got(src, res):
            try:
                info = src.query_info_finish(res)
            except GLib.Error:
                return
            icon = self._place_icon(uri, f) or info.get_icon()
            if icon is not None:
                img.set_from_gicon(icon)
            if not label and info.get_display_name():
                name.set_label(info.get_display_name())
        f.query_info_async('standard::icon,standard::display-name', Gio.FileQueryInfoFlags.NONE,
                           GLib.PRIORITY_DEFAULT, None, got)
        btn.connect('clicked', lambda *_: self._open_place(uri))
        click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        click.connect('pressed', lambda _g, _n, x, y: self._shortcut_menu(btn, uri, x, y))
        btn.add_controller(click)
        return btn

    def _place_icon(self, uri, f):
        """A place's icon (Shortcuts, title, address; the taskbar does the same,
        explorerIcons.js): the chosen one (SHORTCUT_ICONS) or, at the root of a
        mounted disk (the link to /mnt/hdd, for example), XP's disk icon — a
        network one for network file systems. Recent and Favorites with the
        sidebar's colour icons."""
        special = SCHEME_ICONS.get(f.get_uri_scheme() or '')
        if special:
            return Gio.ThemedIcon.new(special)
        try:
            with open(SHORTCUT_ICONS, encoding='utf-8') as fh:
                chosen = json.load(fh)
        except (OSError, ValueError):
            chosen = {}
        name = chosen.get(uri) or chosen.get(self._same_uri(uri))
        if name:
            return Gio.ThemedIcon.new(name)
        path = f.get_path()
        real = os.path.realpath(path) if path else None
        if real and real != '/' and os.path.ismount(real):
            entry = Gio.unix_mount_at(real)[0]
            fstype = Gio.unix_mount_get_fs_type(entry) if entry is not None else ''
            return Gio.ThemedIcon.new('folder-remote' if fstype in NETWORK_FS else 'drive-harddisk')
        return None

    def _shortcut_menu(self, btn, uri, x, y):
        menu = Gio.Menu()
        top = Gio.Menu()
        for text, action in (('open', 'xp.open-place'), ('open-window', 'xp.open-place-window')):
            item = Gio.MenuItem.new(T[text], None)
            item.set_action_and_target_value(action, GLib.Variant('s', uri))
            top.append_item(item)
        menu.append_section(None, top)
        bottom = Gio.Menu()
        item = Gio.MenuItem.new(T['remove-shortcut'], None)
        item.set_action_and_target_value('xp.remove-shortcut', GLib.Variant('s', uri))
        bottom.append_item(item)
        menu.append_section(None, bottom)
        # (hung on the section and not on the button: inside the button it
        # inherited its underline and colour on hover)
        holder = self.shortcuts_section
        ok, pt = btn.compute_point(holder, Graphene.Point().init(x, y))
        pop = Gtk.PopoverMenu.new_from_model(menu)
        pop.set_parent(holder)
        pop.set_has_arrow(False)
        pop.set_position(Gtk.PositionType.BOTTOM)
        rect = Gdk.Rectangle()
        rect.x, rect.y = (int(pt.x), int(pt.y)) if ok else (int(x), int(y))
        rect.width = rect.height = 1
        pop.set_pointing_to(rect)
        # (the menu leaves the section when it closes)
        pop.connect('closed', lambda p: GLib.idle_add(lambda: p.unparent() and False))
        pop.popup()

    def _menu_shortcut(self, pop):
        """"Adicionar atalho" (or "Remover atalho") in the right-click menu: the
        selected folder's, or the background's for the open folder."""
        model = pop.get_menu_model()
        if not isinstance(model, Gio.Menu):
            return
        for i in reversed(range(model.get_n_items())):
            if model.get_item_attribute_value(i, 'zxp-shortcut', None) is not None:
                model.remove(i)
        uri = None
        if menu_has_action(model, 'view.current-directory-properties'):
            slot = self._slot()
            loc = slot.get_property('location') if slot else None
            uri = loc.get_uri() if loc else None
            # before Properties (the last section)
            pos = max(0, model.get_n_items() - 1)
        elif menu_has_action(model, 'view.cut'):
            sel = self._selection()
            if len(sel) == 1 and Nautilus.FileInfo.is_directory(sel[0]):
                uri = Nautilus.FileInfo.get_uri(sel[0])
            # after Open
            pos = next((i + 1 for i in range(model.get_n_items())
                        if menu_has_action_at(model, i, 'view.open-item-new-window')), 1)
        if not uri or not self._can_shortcut(uri):
            return
        on = self._is_shortcut(uri)
        item = Gio.MenuItem.new(T['remove-shortcut' if on else 'add-shortcut'], None)
        item.set_action_and_target_value('xp.remove-shortcut' if on else 'xp.add-shortcut',
                                         GLib.Variant('s', uri))
        section_menu = Gio.Menu()
        section_menu.append_item(item)
        section = Gio.MenuItem.new_section(None, section_menu)
        section.set_attribute_value('zxp-shortcut', GLib.Variant('b', True))
        model.insert_item(min(pos, model.get_n_items()), section)

    def _menu_terminal(self, pop):
        """"Abrir num terminal" in the folder background's menu, right above
        Properties (in its section), for folders on disk; it replaces Nautilus's
        "Abrir na Consola"."""
        model = pop.get_menu_model()
        if not isinstance(model, Gio.Menu) or not menu_has_action(model, 'view.current-directory-properties'):
            return
        slot = self._slot()
        loc = slot.get_property('location') if slot else None
        local = bool(loc and loc.get_path())
        # (Nautilus's own "Abrir na Consola" only opens GNOME Console: this one
        # takes its place)
        for i in range(model.get_n_items()):
            section = model.get_item_link(i, Gio.MENU_LINK_SECTION)
            if isinstance(section, Gio.Menu):
                for j in reversed(range(section.get_n_items())):
                    if menu_has_action_at(section, j, 'view.current-directory-console') and \
                            section.get_item_link(j, Gio.MENU_LINK_SECTION) is None:
                        section.remove(j)
        for i in range(model.get_n_items()):
            section = model.get_item_link(i, Gio.MENU_LINK_SECTION)
            if not isinstance(section, Gio.Menu) or \
                    not menu_has_action(section, 'view.current-directory-properties'):
                continue
            ours = next((j for j in range(section.get_n_items())
                         if section.get_item_attribute_value(j, 'zxp-terminal', None) is not None), None)
            if ours is not None and not local:
                section.remove(ours)
            elif ours is None and local:
                item = Gio.MenuItem.new(T['open-terminal'], 'xp.open-terminal')
                item.set_attribute_value('zxp-terminal', GLib.Variant('b', True))
                at = next(j for j in range(section.get_n_items())
                          if menu_has_action_at(section, j, 'view.current-directory-properties'))
                section.insert_item(at, item)
            return

    def _open_terminal(self):
        """The system's terminal (x-terminal-emulator, the Start menu's one) in
        the open folder."""
        slot = self._slot()
        loc = slot.get_property('location') if slot else None
        path = loc.get_path() if loc else None
        if not path:
            return
        for cmd in ('x-terminal-emulator', 'gnome-terminal', 'kgx', 'ptyxis', 'xterm'):
            if GLib.find_program_in_path(cmd):
                launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.NONE)
                launcher.set_cwd(path)
                try:
                    launcher.spawnv([cmd])
                except GLib.Error as e:
                    print(f'Zorin XP: terminal: {e}')
                return

    # --------------------------------------------- tarefas e detalhes
    def _selection(self):
        """Files selected in the current view (Gio.File, Nautilus's FileInfo)."""
        view = self._files_view()
        widget = (find(view, 'GtkGridView') or find(view, 'GtkColumnView')) if view else None
        model = widget.get_model() if widget else None
        if model is None:
            return []
        if not getattr(model, '_zxp_watch', False):
            model._zxp_watch = True
            model.connect('selection-changed', lambda *_: self._sync_details())
            model.connect('items-changed', lambda *_: GLib.idle_add(
                lambda: self._sync_details() and False))
        out = []
        bits = model.get_selection()
        it_ok, it, pos = Gtk.BitsetIter.init_first(bits)
        while it_ok and len(out) < 1000:
            item = model.get_item(pos)
            if isinstance(item, Gtk.TreeListRow):   # (list view)
                item = item.get_item()
            f = item.get_property('file') if item is not None else None
            if f is not None:
                out.append(f)
            it_ok, pos = it.next()
        return out

    def _folder_kind(self, loc):
        path = loc.get_path() if loc else None
        if not path:
            return None
        U = GLib.UserDirectory
        for kind, d in (('music', U.DIRECTORY_MUSIC), ('pictures', U.DIRECTORY_PICTURES),
                        ('videos', U.DIRECTORY_VIDEOS)):
            base = GLib.get_user_special_dir(d)
            if base and base != GLib.get_home_dir() and (path == base or path.startswith(base + '/')):
                return kind
        return None

    def _media(self, loc, prefix, limit=500):
        """URIs of the files of a type (audio/, image/, video/) in the folder."""
        out = []
        try:
            en = loc.enumerate_children('standard::name,standard::content-type',
                                        Gio.FileQueryInfoFlags.NONE, None)
            for info in en:
                if len(out) >= limit:
                    break
                if (info.get_content_type() or '').startswith(prefix):
                    out.append(loc.get_child(info.get_name()).get_uri())
        except GLib.Error:
            pass
        return sorted(out)

    def _launch(self, uris):
        if not uris:
            return
        try:
            ctype = Gio.File.new_for_uri(uris[0]).query_info(
                'standard::content-type', Gio.FileQueryInfoFlags.NONE, None).get_content_type()
            app = Gio.AppInfo.get_default_for_type(ctype, False)
            if app:
                app.launch_uris(uris, None)
        except GLib.Error:
            pass

    def _set_background(self, uri):
        bg = Gio.Settings.new('org.gnome.desktop.background')
        bg.set_string('picture-uri', uri)
        bg.set_string('picture-uri-dark', uri)

    def _sync_special(self, loc, files):
        kind = self._folder_kind(loc)
        tasks = []
        if kind == 'music':
            uris = self._media(loc, 'audio/')
            if uris:
                tasks.append(('play', T['play-all'], lambda u=uris: self._launch(u)))
        elif kind == 'videos':
            uris = self._media(loc, 'video/')
            if uris:
                tasks.append(('play', T['play-all'], lambda u=uris: self._launch(u)))
        elif kind == 'pictures':
            uris = self._media(loc, 'image/')
            if uris:
                tasks.append(('slideshow', T['slideshow'], lambda u=uris: self._launch(u)))
            if len(files) == 1:
                ctype = ''
                try:
                    ctype = files[0].query_info('standard::content-type', Gio.FileQueryInfoFlags.NONE,
                                                None).get_content_type() or ''
                except GLib.Error:
                    pass
                if ctype.startswith('image/'):
                    uri = files[0].get_uri()
                    tasks.append(('background', T['set-background'], lambda u=uri: self._set_background(u)))
        child = self.special_slot.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.special_slot.remove(child)
            child = nxt
        if not kind:
            return
        if not tasks:
            # folder still without files: the section stays, with the task disabled
            tasks.append(('slideshow' if kind == 'pictures' else 'play',
                          T['slideshow' if kind == 'pictures' else 'play-all'], None))
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for icon, text, fn in tasks:
            btn = self._task(icon, text, None)
            if fn:
                btn.connect('clicked', lambda *_a, f=fn: f())
            else:
                btn.set_sensitive(False)
            body.append(btn)
        self.special_slot.append(self._section(T[f'{kind}-tasks'], body, special=kind))

    def _sync_details(self):
        if not hasattr(self, 'tasks_box'):
            return False
        sel = self._selection()
        files = []
        for f in sel:
            try:
                files.append(Gio.File.new_for_uri(Nautilus.FileInfo.get_uri(f)))
            except Exception:
                pass

        slot = getattr(self, '_slot_obj', None)
        self._sync_special(slot.get_property('location') if slot else None, files)

        # tarefas
        child = self.tasks_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.tasks_box.remove(child)
            child = nxt
        if not files:
            self.tasks_section._zxp_label.set_label(T['file-tasks'])
            self.tasks_box.append(self._task('new-folder', T['task-new-folder'], 'new-folder'))
        else:
            is_dir = len(files) == 1 and files[0].query_file_type(
                Gio.FileQueryInfoFlags.NONE, None) == Gio.FileType.DIRECTORY
            what = 'many' if len(files) > 1 else ('folder' if is_dir else 'file')
            for icon, action in (('rename', 'rename'), ('move', 'move-to'),
                                 ('copy', 'copy-to'), ('delete', 'move-to-trash')):
                if icon == 'rename' and what == 'many':
                    continue
                self.tasks_box.append(self._task(icon, T[f'task-{icon}-{what}'], action))

        # details: the selected item, or the open folder
        child = self.details_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.details_box.remove(child)
            child = nxt
        self._details_uri = None
        target = files[0] if len(files) == 1 else None
        if target is None and not files:
            slot = getattr(self, '_slot_obj', None)
            target = slot.get_property('location') if slot else None
        if len(files) > 1:
            self.details_box.append(Gtk.Label(label=T['n-selected'].format(len(files)), xalign=0,
                                              wrap=True, css_classes=['zxp-details-count']))
            # total size of the files (folders do not count, as in XP)
            total, any_file = 0, False
            for f in files:
                try:
                    i = f.query_info('standard::type,standard::size', Gio.FileQueryInfoFlags.NONE, None)
                except GLib.Error:
                    continue
                if i.get_file_type() != Gio.FileType.DIRECTORY:
                    total += i.get_size()
                    any_file = True
            if any_file:
                self.details_box.append(Gtk.Label(label=T['total-size'].format(human_size(total)),
                                                  xalign=0, wrap=True, css_classes=['zxp-details-first']))
            return False
        if target is None:
            return False
        try:
            info = target.query_info('standard::display-name,standard::type,standard::size,'
                                     'standard::content-type,time::modified',
                                     Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error:
            return False
        is_dir = info.get_file_type() == Gio.FileType.DIRECTORY
        ctype = info.get_content_type() or ''
        lines = []
        self._details_uri = target.get_uri()
        if ctype.startswith('image/') and target.get_path():
            fmt, w, h = GdkPixbuf.Pixbuf.get_file_info(target.get_path())
            if fmt:
                lines.append(T['dimensions'].format(w, h))
                self._preview_image(target.get_path(), self._details_uri)
        elif ctype == 'application/pdf' and target.get_path():
            # (as XP had no PDF thumbnails on the icons, the first page shows here,
            # in Details)
            self._preview_pdf(target, info, self._details_uri)
        name = Gtk.Label(label=info.get_display_name(), xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                         css_classes=['zxp-details-name'])
        self.details_box.append(name)
        kind = T['folder-type'] if is_dir else (Gio.content_type_get_description(ctype) if ctype else '')
        self.details_box.append(Gtk.Label(label=kind, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR))
        if not is_dir:
            lines.append(T['size-line'].format(human_size(info.get_size())))
        dt = info.get_modification_date_time()
        if dt:
            lines.append(T['modified-line'].format(long_date(dt.to_local())))
        for i, text in enumerate(lines):
            lbl = Gtk.Label(label=text, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
            if i == 0:
                lbl.add_css_class('zxp-details-first')
            self.details_box.append(lbl)
        return False

    # ----------------------------------------------- right-click menu
    # On the folder background, as in XP: "Ver" (the Explorer's views),
    # "Dispor ícones por" (Name, Size, Type, Modified: Nautilus's sorting,
    # with the dot on the chosen one) and "Actualizar", on top of what
    # Nautilus already has. The menu is a popover child of the view, created
    # on the first click.
    def _hook_menus(self, view):
        if view is None or getattr(view, '_zxp_menus', False):
            return False
        view._zxp_menus = True
        # (the list must stay stored: freed, it stops notifying)
        children = view._zxp_children = view.observe_children()

        def check(*_):
            for i in range(children.get_n_items()):
                pop = children.get_item(i)
                if isinstance(pop, Gtk.PopoverMenu) and not getattr(pop, '_zxp_menu', False):
                    pop._zxp_menu = True
                    # cascading submenus, to the side (GTK slides them inside the same menu)
                    pop.set_flags(Gtk.PopoverMenuFlags.NESTED)
                    pop.connect('notify::menu-model', lambda p, _x: self._xp_background_menu(p))
                    pop.connect('notify::visible', lambda p, _x: p.get_visible() and (
                        swap_menu_actions(p.get_menu_model()),
                        self._xp_background_menu(p), self._menu_shortcut(p), self._menu_terminal(p)))
                    self._xp_background_menu(pop)
                elif pop.__gtype__.name == 'NautilusRenameFilePopover' and \
                        not getattr(pop, '_zxp_menu', False):
                    # (Nautilus's "Rename", if it still shows: XP's)
                    pop._zxp_menu = True
                    # (after the focus goes back to the view, otherwise the box closes at once)
                    pop.connect('notify::visible', lambda p, _x: p.get_visible() and (
                        p.popdown(), GLib.timeout_add(150, lambda: self._rename_selected() and False)))
        children.connect('items-changed', lambda *_: check())
        check()
        return False

    def _xp_background_menu(self, pop):
        model = pop.get_menu_model()
        if not isinstance(model, Gio.Menu) or model.get_n_items() == 0:
            return
        if model.get_item_attribute_value(0, 'zxp', None) is not None:
            return                                  # (it is already there)
        if not menu_has_action(model, 'view.current-directory-properties'):
            return                                  # (it is the selected items' menu)
        views = Gio.Menu()
        for key in VIEW_MODES:
            views.append(T[key], f'xp.view-mode::{key}')
        arrange = Gio.Menu()
        for key, target in ARRANGE:
            item = Gio.MenuItem.new(T[f'arrange-{key}'], None)
            item.set_action_and_target_value('view.sort', GLib.Variant('(sb)', target))
            arrange.append_item(item)
        top = Gio.Menu()
        top.append_submenu(T['view'], views)
        top.append_submenu(T['arrange'], arrange)
        top.append(T['refresh'], 'win.reload')
        section = Gio.MenuItem.new_section(None, top)
        section.set_attribute_value('zxp', GLib.Variant('b', True))
        # the loose items at the start (New Folder, New Document...) in a section,
        # so the separator line sits below ours, as in XP
        loose = Gio.Menu()
        while model.get_n_items() and not menu_item_is_section(model, 0):
            loose.append_item(Gio.MenuItem.new_from_model(model, 0))
            model.remove(0)
        if loose.get_n_items():
            model.insert_section(0, None, loose)
        model.insert_item(0, section)

    # ------------------------------------------- preview (Details)
    def _preview_size(self):
        width = self.details_box.get_width()
        return (min(PREVIEW_MAX[0], width) if width > 0 else PREVIEW_MAX[0]), PREVIEW_MAX[1]

    def _preview_image(self, path, uri):
        """The image scaled down to fit the pane (never bigger than the original):
        the pane always has the same width."""
        max_w, max_h = self._preview_size()
        try:
            stream = Gio.File.new_for_path(path).read(None)
        except GLib.Error:
            return

        def done(_src, res):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(res)
            except GLib.Error:
                return
            if getattr(self, '_details_uri', None) != uri:
                return                          # (the selection changed in the meantime)
            pic = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            pic.set_can_shrink(False)
            pic.set_halign(Gtk.Align.CENTER)
            pic.add_css_class('zxp-details-preview')
            self.details_box.prepend(pic)
        fmt, w, h = GdkPixbuf.Pixbuf.get_file_info(path)
        if fmt and w <= max_w and h <= max_h:
            max_w, max_h = w, h
        GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream, max_w, max_h, True, None, done)

    def _preview_pdf(self, target, info, uri):
        """The PDF's first page (evince-thumbnailer, in a cached copy)."""
        import hashlib
        mtime = info.get_modification_date_time()
        key = hashlib.md5(f'{uri} {mtime.to_unix() if mtime else 0}'.encode()).hexdigest()
        png = os.path.join(PREVIEW_CACHE, f'{key}.png')
        if os.path.exists(png):
            self._preview_image(png, uri)
            return
        tool = GLib.find_program_in_path('evince-thumbnailer')
        if not tool:
            return
        os.makedirs(PREVIEW_CACHE, exist_ok=True)
        # (Evince's AppArmor only lets the thumbnailer write to
        # /tmp/gnome-desktop-*: the image moves to the cache afterwards)
        tmp = f'/tmp/gnome-desktop-zxp-{key}.png'
        try:
            proc = Gio.Subprocess.new([tool, '-s', '256', uri, tmp], Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error:
            return

        def done(p, res):
            try:
                p.wait_finish(res)
            except GLib.Error:
                return
            if not os.path.exists(tmp):
                return
            try:
                import shutil
                shutil.move(tmp, png)
            except OSError:
                return
            if getattr(self, '_details_uri', None) == uri:
                self._preview_image(png, uri)
        proc.wait_async(None, done)

    # ------------------------------------------------- local e pesquisa
    def _follow_slot(self):
        slot = self._slot()
        if not slot or getattr(self, '_slot_obj', None) is slot:
            return
        if getattr(self, '_slot_obj', None) and self._slot_handler:
            self._slot_obj.disconnect(self._slot_handler)
        first = getattr(self, '_slot_obj', None) is None
        self._slot_obj = slot
        self._slot_handler = slot.connect('notify::location', lambda *_: self._sync_location())
        if first:
            # saved XP view (or Icons at 48 px, instead of the huge folders),
            # applied when the first folder already has a view
            def apply_mode(tries=[20]):
                if self._files_view() is None and tries[0] > 0:
                    tries[0] -= 1
                    return True
                self.win.activate_action('xp.view-mode', GLib.Variant('s', load_view_mode()))
                return False
            GLib.timeout_add(100, apply_mode)
        self._sync_location()
        # the flag animates while the folder loads
        if getattr(self, '_loading_handler', None) and getattr(self, '_loading_slot', None):
            self._loading_slot.disconnect(self._loading_handler)
        self._loading_slot = slot
        try:
            self._loading_handler = slot.connect(
                'notify::loading', lambda s, _p: self._animate_brand(s.get_property('loading')))
        except TypeError:
            self._loading_handler = None

    def _location_scheme(self):
        slot = getattr(self, '_slot_obj', None)
        loc = slot.get_property('location') if slot else None
        return loc.get_uri_scheme() if loc is not None else None

    def _sync_title(self, *_):
        # the same name as the sidebar's (Nautilus puts "Recent" in the title)
        if self._location_scheme() == 'recent' and self.win.get_title() != T['recent']:
            self.win.set_title(T['recent'])

    def _sync_location(self):
        if not getattr(self, '_title_watch', False):
            self._title_watch = True
            self.win.connect('notify::title', self._sync_title)
        GLib.idle_add(lambda: self._sync_title() and False)
        nav_click()
        GLib.idle_add(lambda: self._hook_menus(self._files_view()) and False)
        GLib.idle_add(lambda: self._sync_tiles() and False)
        GLib.timeout_add(300, lambda: self._sync_details() and False)
        slot = self._slot_obj
        loc = slot.get_property('location') if slot else None
        if not loc:
            return
        self.entry.set_text(loc.get_path() or loc.get_uri())
        self.entry.set_position(-1)

        def done(f, res):
            try:
                info = f.query_info_finish(res)
            except GLib.Error:
                return
            gicon = self._place_icon(loc.get_uri(), loc) or info.get_icon()
            self.title_icon.set_from_gicon(gicon)
            self.entry.set_icon_from_gicon(Gtk.EntryIconPosition.PRIMARY, gicon)
        loc.query_info_async('standard::icon', Gio.FileQueryInfoFlags.NONE,
                             GLib.PRIORITY_DEFAULT, None, done)

    def _go(self):
        # the address goes to Nautilus's own location box
        text = self.entry.get_text().strip()
        loc_entry = find(self.content_tv, 'NautilusLocationEntry')
        if not text or not loc_entry:
            return
        loc_entry.set_text(text)
        loc_entry.emit('activate')

    def _on_search(self, btn):
        slot = self._slot()
        self.content_tv.set_reveal_top_bars(btn.get_active())
        if slot:
            slot.activate_action('slot.search-visible', None)


def menu_item_is_section(model, i):
    links = model.iterate_item_links(i)
    while links.next():
        if links.get_name() == 'section':
            return True
    return False


def menu_has_action_at(model, i, action):
    value = model.get_item_attribute_value(i, 'action', None)
    if value is not None and value.get_string() == action:
        return True
    links = model.iterate_item_links(i)
    while links.next():
        if menu_has_action(links.get_value(), action):
            return True
    return False


def menu_has_action(model, action):
    for i in range(model.get_n_items()):
        value = model.get_item_attribute_value(i, 'action', None)
        if value is not None and value.get_string() == action:
            return True
        links = model.iterate_item_links(i)
        while links.next():
            if menu_has_action(links.get_value(), action):
                return True
    return False


class _Click:
    media = None
    last = 0
    sound = None


def nav_click():
    """The XP Explorer's click when opening a folder (once per change)."""
    now = GLib.get_monotonic_time() // 1000
    if now - _Click.last < NAV_QUIET_MS:
        return
    _Click.last = now
    play_sound(NAV_SOUND)


_SOUNDS = {}


def play_sound(path):
    """A sound from XP's scheme (if event sounds are on)."""
    if _Click.sound is None:
        _Click.sound = Gio.Settings.new('org.gnome.desktop.sound')
    if not _Click.sound.get_boolean('event-sounds') or not os.path.exists(path):
        return
    media = _SOUNDS.get(path)
    if media is None:
        media = _SOUNDS[path] = Gtk.MediaFile.new_for_filename(path)
    media.seek(0)
    media.play()


def swap_menu_actions(model):
    """The Nautilus menu items that open its own windows (new folder, rename,
    delete without asking) now do what XP does."""
    if not isinstance(model, Gio.Menu):
        return
    for i in range(model.get_n_items()):
        value = model.get_item_attribute_value(i, 'action', None)
        action = value.get_string() if value is not None else None
        if action in SWAPPED_ACTIONS:
            item = Gio.MenuItem.new_from_model(model, i)
            item.set_action_and_target_value(SWAPPED_ACTIONS[action], None)
            model.remove(i)
            model.insert_item(i, item)
        links = model.iterate_item_links(i)
        while links.next():
            swap_menu_actions(links.get_value())


def xp_wrap(text, width, measure, lines=2):
    """text in up to `lines` lines of `width` px, like XP's DrawText with
    DT_WORDBREAK | DT_END_ELLIPSIS: breaks at spaces; a word wider than the
    line is cut with "..." and ends there; the last line takes the rest of
    the text, cut at the end. lines=None: the whole text (the focused item's
    name in XP), with long words broken where the line ends."""
    if measure(text) <= width:
        return text

    def fits(t):                        # the longest start of t that fits (>= 1)
        lo, hi = 1, len(t)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if measure(t[:mid]) <= width:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def cut(t):
        if measure(t) <= width:
            return t
        lo, hi = 0, len(t)
        while lo < hi:                  # the longest start that fits with "..."
            mid = (lo + hi + 1) // 2
            if measure(t[:mid].rstrip() + '...') <= width:
                lo = mid
            else:
                hi = mid - 1
        return t[:lo].rstrip() + '...'
    out = []
    rest = text
    while rest and (lines is None or len(out) < lines):
        if lines is not None and len(out) == lines - 1:
            out.append(cut(rest))
            break
        words = rest.split(' ')
        line = words[0]
        if measure(line) > width:
            if lines is None:
                n = fits(line)
                out.append(line[:n])
                rest = rest[n:]
                continue
            out.append(cut(line))
            break
        i = 1
        while i < len(words) and measure(line + ' ' + words[i]) <= width:
            line += ' ' + words[i]
            i += 1
        out.append(line)
        rest = ' '.join(words[i:])
    return '\n'.join(out)


def human_size(n):
    """Tamanho como no XP (3 algarismos): 54,4 KB, 1,21 MB, 512 bytes."""
    if n < 1024:
        return f'{n} bytes'
    for unit in ('KB', 'MB', 'GB', 'TB'):
        n /= 1024
        if n < 1000 or unit == 'TB':
            text = f'{n:.3g}' if n < 100 else f'{n:.0f}'
            return (text.replace('.', ',') if LANG == 'pt' else text) + ' ' + unit
    return ''


def long_date(dt):
    return T['long-date'].format(wd=T['weekdays'][dt.get_day_of_week() - 1], d=dt.get_day_of_month(),
                                 m=T['months'][dt.get_month() - 1], y=dt.get_year(),
                                 t=dt.format('%H:%M'))


def load_view_mode():
    kf = GLib.KeyFile()
    try:
        kf.load_from_file(STATE_FILE, GLib.KeyFileFlags.NONE)
        key = kf.get_string('explorer', 'view')
        return key if key in VIEW_MODES else DEFAULT_VIEW
    except GLib.Error:
        return DEFAULT_VIEW


def save_view_mode(key):
    kf = GLib.KeyFile()
    kf.set_string('explorer', 'view', key)
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    kf.save_to_file(STATE_FILE)


def on_window(_app, win):
    if win.__gtype__.name != 'NautilusWindow' or getattr(win, '_zxp', None):
        return

    # when the window is created it does not have its content yet: rearrange
    # when it is being prepared to show (before the first draw)
    def apply(*_):
        if getattr(win, '_zxp', None) is None and win.get_content() is not None:
            try:
                win._zxp = XpExplorer(win)
            except Exception as e:  # never stop Nautilus from opening
                print(f'Zorin XP: {e}')
                win._zxp = False
    if win.get_realized():
        apply()
    else:
        win.connect('realize', apply)


app = Gio.Application.get_default()
if app is not None:
    app.connect('window-added', on_window)
    for w in app.get_windows():
        on_window(app, w)


def _xp_size(info):
    # XP's Details: always in KB, rounded up, with a thousands separator;
    # empty for folders
    kb = (info.get_size() + 1023) // 1024
    return f'{kb:,}'.replace(',', '.' if LANG == 'pt' else ',') + ' KB'


def _xp_type(ctype):
    # the type capitalised, like the ones in XP's registry ("Imagem JPEG")
    text = Gio.content_type_get_description(ctype) if ctype else ''
    return text[:1].upper() + text[1:]


def _image_size(loc, ctype):
    """"960 x 957" for local images (only reads the header)."""
    path = loc.get_path()
    if not path or not ctype.startswith('image/'):
        return ''
    try:
        fmt, w, h = GdkPixbuf.Pixbuf.get_file_info(path)
    except GLib.Error:
        return ''
    return f'{w} x {h}' if fmt is not None and w > 0 and h > 0 else ''


class ZorinXpExplorer(GObject.GObject, Nautilus.ColumnProvider, Nautilus.InfoProvider):
    """Details columns with XP's formats (size in KB, "Pasta de ficheiros",
    date dd-mm-yyyy hh:mm)."""

    def get_columns(self):
        return (
            Nautilus.Column(name='zxp_size', attribute='zxp_size',
                            label=T['col-size'], description=T['col-size']),
            Nautilus.Column(name='zxp_type', attribute='zxp_type',
                            label=T['col-type'], description=T['col-type']),
            Nautilus.Column(name='zxp_date', attribute='zxp_date',
                            label=T['col-date_modified'], description=T['col-date_modified']),
        )

    def update_file_info(self, file):
        loc = file.get_location()
        if loc is None:
            return
        try:
            info = loc.query_info('standard::type,standard::size,standard::content-type,'
                                  'time::modified', Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error:
            return
        is_dir = info.get_file_type() == Gio.FileType.DIRECTORY
        size = '' if is_dir else _xp_size(info)
        file.add_string_attribute('zxp_size', size)
        ctype = info.get_content_type() or ''
        kind = T['folder-type'] if is_dir else _xp_type(ctype)
        file.add_string_attribute('zxp_type', kind)
        # Tiles (a two-line caption, as in XP): images with the dimensions and the
        # type, other files with the type and size, folders with the name only

        tile = ''
        if not is_dir:
            dims = _image_size(loc, ctype)
            tile = f'{dims}\n{kind}' if dims else f'{kind}\n{size}'
        file.add_string_attribute('zxp_tile', tile)
        dt = info.get_modification_date_time()
        file.add_string_attribute('zxp_date', dt.to_local().format('%d-%m-%Y %H:%M') if dt else '')
