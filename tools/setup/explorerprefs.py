#!/usr/bin/env python3
"""Files as the XP Explorer: GNOME settings (install.sh's explorer
component).

  apply   no PDF thumbnails on the icons, as in XP (the first page shows in
          Details, src/nautilus-xp): application/pdf joins the types without
          thumbnails (org.gnome.desktop.thumbnailers disable) and the PDF
          thumbnails already made leave the cache (~/.cache/thumbnails; they
          are made again if the setting goes back)
  undo    restores the previous list

State in ~/.local/share/zorin-xp/explorer.json.
"""
import json
import os
import struct
import sys

import gi

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib  # noqa: E402

SCHEMA, KEY = 'org.gnome.desktop.thumbnailers', 'disable'
PDF = 'application/pdf'
STATE = os.path.join(GLib.get_user_data_dir(), 'zorin-xp', 'explorer.json')


def _thumb_text(path):
    """The tEXt entries of a PNG (Thumb::URI, Thumb::Mimetype...)."""
    out = {}
    try:
        with open(path, 'rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                return out
            while True:
                head = f.read(8)
                if len(head) < 8:
                    break
                size, kind = struct.unpack('>I4s', head)
                if kind == b'IDAT':
                    break
                data = f.read(size)
                f.read(4)                           # CRC
                if kind == b'tEXt' and b'\0' in data:
                    k, v = data.split(b'\0', 1)
                    out[k.decode('latin-1')] = v.decode('latin-1')
    except OSError:
        pass
    return out


def clear_pdf_thumbnails():
    base = os.path.join(GLib.get_user_cache_dir(), 'thumbnails')
    removed = 0
    for root, _dirs, files in os.walk(base):
        for name in files:
            if not name.endswith('.png'):
                continue
            path = os.path.join(root, name)
            text = _thumb_text(path)
            if text.get('Thumb::Mimetype') == PDF or text.get('Thumb::URI', '').lower().endswith('.pdf'):
                os.remove(path)
                removed += 1
    return removed


def apply():
    settings = Gio.Settings.new(SCHEMA)
    current = list(settings.get_strv(KEY))
    if not os.path.exists(STATE):
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, 'w') as f:
            json.dump({'thumbnailers-disable': current}, f)
    if PDF not in current:
        settings.set_strv(KEY, current + [PDF])
    Gio.Settings.sync()
    print(f'  miniaturas de PDF tiradas da cache: {clear_pdf_thumbnails()}')


def undo():
    if not os.path.exists(STATE):
        return
    with open(STATE) as f:
        saved = json.load(f)
    settings = Gio.Settings.new(SCHEMA)
    settings.set_strv(KEY, saved.get('thumbnailers-disable', []))
    Gio.Settings.sync()
    os.remove(STATE)


if __name__ == '__main__':
    {'apply': apply, 'undo': undo}[sys.argv[1]]()
