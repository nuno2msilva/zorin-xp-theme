#!/usr/bin/env python3
"""Layout do Zorin para o tema XP: o estilo "Windows" da Aparência do Zorin
(menu com todas as aplicações + zorin-taskbar, a opção de lista de janelas
que lembra o Windows 7) com os ajustes do XP por cima.

Aplica o mesmo que a Aparência do Zorin aplica para esse estilo
(zorin_appearance/Layouts/20-windows-list-shell.py) e depois as definições
aprovadas para o XP:
  - barra de 30 px em todos os monitores;
  - botões das janelas com texto, largura fixa de 120 px, sem agrupar;
  - pré-visualizações das janelas e dicas;
  - sem botão Atividades nem "Mostrar aplicações"; "Ver ADT" (mostrar o
    ambiente de trabalho) visível, junto ao relógio;
  - área de notificação, menu do sistema e relógio à direita;
  - sem transparências nem bordas arredondadas.
A cópia de segurança do instalador (/org/gnome/shell/) permite repor tudo.
"""
import json

from gi.repository import Gio, GLib
import os
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TB = 'org.gnome.shell.extensions.zorin-taskbar'

# o estilo Windows da Aparência do Zorin
ENABLE = ['zorin-menu@zorinos.com', 'zorin-taskbar@zorinos.com']
DISABLE = ['add-to-desktop@tommimon.github.com',
           'apps-menu@gnome-shell-extensions.gcampax.github.com',
           'places-menu@gnome-shell-extensions.gcampax.github.com',
           'zorin-dash@zorinos.com',
           'zorin-hide-activities-move-clock@zorinos.com']
ZORIN_WINDOWS_LAYOUT = [
    ('org.gnome.desktop.interface', 'enable-hot-corners', GLib.Variant('b', False)),
    ('org.gnome.desktop.interface', 'zorin-display-overview-on-startup', GLib.Variant('b', False)),
    ('org.gnome.shell.extensions.zorin-menu', 'layout', GLib.Variant('s', 'ALL')),
    (TB, 'activate-single-window', GLib.Variant('b', True)),
    (TB, 'click-action', GLib.Variant('s', 'CYCLE-MIN')),
    (TB, 'dot-style-focused', GLib.Variant('s', 'CILIORA')),
    (TB, 'dot-style-unfocused', GLib.Variant('s', 'DOTS')),
    (TB, 'group-apps-use-launchers', GLib.Variant('b', False)),
    (TB, 'intellihide', GLib.Variant('b', False)),
    (TB, 'multi-monitors', GLib.Variant('b', False)),
    (TB, 'panel-element-positions-monitors-sync', GLib.Variant('b', True)),
    (TB, 'panel-lengths', GLib.Variant('s', '{}')),
    (TB, 'panel-positions', GLib.Variant('s', '{}')),
    (TB, 'peek-mode', GLib.Variant('b', True)),
    (TB, 'stockgs-keep-top-panel', GLib.Variant('b', False)),
    (TB, 'show-favorites', GLib.Variant('b', True)),
    (TB, 'show-favorites-all-monitors', GLib.Variant('b', True)),
    (TB, 'show-running-apps', GLib.Variant('b', True)),
    (TB, 'window-preview-size', GLib.Variant('i', 200)),
    ('org.gnome.nautilus.preferences', 'click-policy', GLib.Variant('s', 'double')),
]

# por cima: o XP
PANEL_SIZE = 30
XP = [
    (TB, 'panel-size', GLib.Variant('i', PANEL_SIZE)),
    (TB, 'group-apps', GLib.Variant('b', False)),
    (TB, 'group-apps-use-fixed-width', GLib.Variant('b', True)),
    (TB, 'group-apps-label-max-width', GLib.Variant('i', 120)),
    (TB, 'show-window-previews', GLib.Variant('b', True)),
    (TB, 'show-tooltip', GLib.Variant('b', True)),
    (TB, 'isolate-workspaces', GLib.Variant('b', True)),
    (TB, 'show-showdesktop-hover', GLib.Variant('b', True)),
    (TB, 'show-showdesktop-icon', GLib.Variant('b', False)),
    (TB, 'showdesktop-button-width', GLib.Variant('i', 3)),
    (TB, 'global-border-radius', GLib.Variant('i', 0)),
    (TB, 'panel-margin', GLib.Variant('i', 0)),
    (TB, 'trans-use-border', GLib.Variant('b', False)),
    (TB, 'trans-use-custom-opacity', GLib.Variant('b', False)),
    (TB, 'trans-use-dynamic-opacity', GLib.Variant('b', False)),
]
# ordem e visibilidade dos elementos (igual em todos os monitores)
ELEMENTS = [
    ('leftBox', True, 'stackedTL'),
    ('showAppsButton', False, 'stackedTL'),
    ('taskbar', True, 'stackedTL'),
    ('centerBox', True, 'stackedBR'),
    ('activitiesButton', False, 'stackedBR'),
    ('rightBox', True, 'stackedBR'),
    ('systemMenu', True, 'stackedBR'),
    ('dateMenu', True, 'stackedBR'),
    ('desktopButton', True, 'stackedBR'),
]
# chaves de monitor que a zorin-taskbar usa (índices e as já guardadas)
MONITOR_KEYS = ['0', '1', '2']


def set_all(settings):
    cache = {}
    for schema, key, value in settings:
        if Gio.SettingsSchemaSource.get_default().lookup(schema, True) is None:
            continue
        s = cache.setdefault(schema, Gio.Settings.new(schema))
        if s.props.settings_schema.has_key(key):
            s.set_value(key, value)


def per_monitor(settings, key, value):
    try:
        cur = json.loads(settings.get_string(key) or '{}')
    except ValueError:
        cur = {}
    keys = set(cur) | set(MONITOR_KEYS)
    settings.set_string(key, json.dumps({k: value for k in sorted(keys)}, separators=(',', ':')))


def main():
    shell = Gio.Settings.new('org.gnome.shell')
    enabled = shell.get_strv('enabled-extensions')
    disabled = shell.get_strv('disabled-extensions')
    for e in DISABLE:
        enabled = [x for x in enabled if x != e]
        if e not in disabled:
            disabled.append(e)
    for e in ENABLE:
        if e not in enabled:
            enabled.append(e)
        disabled = [x for x in disabled if x != e]
    shell.set_strv('enabled-extensions', enabled)
    shell.set_strv('disabled-extensions', disabled)

    set_all(ZORIN_WINDOWS_LAYOUT)
    set_all(XP)
    tb = Gio.Settings.new(TB)
    per_monitor(tb, 'panel-sizes', PANEL_SIZE)
    per_monitor(tb, 'panel-element-positions',
                [{'element': e, 'visible': v, 'position': p} for e, v, p in ELEMENTS])
    Gio.Settings.sync()


if __name__ == '__main__':
    main()
