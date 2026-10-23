#!/usr/bin/env python3
"""Captures GTK4 widgets with the generated theme (use through tools/test/preview.sh).

Usage: gtk4shot.py <out.png> [frame|gallery]
  frame   — simulates mutter-x11-frames' title bar
            (widget.default-decoration > headerbar.titlebar.default-decoration)
  gallery — GTK4 widget gallery
"""
import sys

import gi
import os

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402


class FrameHeader(Gtk.Box):
    """Equivalent to MetaFrameHeader (CSS name "widget")."""
    __gtype_name__ = "ZxpFrameHeader"


FrameHeader.set_css_name("widget")


def frame_titlebar(active=True, maximized=False):
    hdr = FrameHeader()
    hdr.add_css_class("default-decoration")
    hb = Gtk.HeaderBar()
    hb.add_css_class("titlebar")
    hb.add_css_class("default-decoration")
    hb.set_hexpand(True)
    hdr.append(hb)
    return hdr


def gallery():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
        box.set_property(m, 8)
    row = Gtk.Box(spacing=8)
    row.append(Gtk.Button(label="Aplicar"))
    b = Gtk.Button(label="OK")
    b.add_css_class("default")
    row.append(b)
    c = Gtk.CheckButton(label="Marcada")
    c.set_active(True)
    row.append(c)
    row.append(Gtk.Entry(text="Texto"))
    box.append(row)
    row = Gtk.Box(spacing=8)
    dd = Gtk.DropDown.new_from_strings(["Windows XP", "Clássico"])
    row.append(dd)
    sp = Gtk.SpinButton.new_with_range(0, 100, 1)
    row.append(sp)
    pb = Gtk.ProgressBar()
    pb.set_fraction(0.6)
    pb.set_size_request(120, -1)
    row.append(pb)
    box.append(row)
    nb = Gtk.Notebook()
    for t in ("Temas", "Aspeto"):
        nb.append_page(Gtk.Label(label=f"Conteúdo de {t}"), Gtk.Label(label=t))
    nb.set_size_request(300, 80)
    box.append(nb)
    return box


def main():
    out = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "frame"
    s = Gtk.Settings.get_default()
    s.set_property("gtk-font-name", "Tahoma 8.25")
    s.set_property("gtk-decoration-layout", ":minimize,maximize,close")
    s.set_property("gtk-xft-hintstyle", "hintfull")
    win = Gtk.Window(title="Sem título - Bloco de notas")
    win.set_decorated(False)
    if mode == "frame":
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(frame_titlebar())
        filler = Gtk.Box()
        filler.set_size_request(400, 40)
        content.append(filler)
        win.set_child(content)
        target = content
    else:
        target = gallery()
        win.set_child(target)
    win.present()
    loop = GLib.MainLoop()

    def snap():
        w, h = target.get_width(), target.get_height()
        paint = Gtk.WidgetPaintable.new(target)
        snapshot = Gtk.Snapshot()
        paint.snapshot(snapshot, w, h)
        node = snapshot.to_node()
        tex = win.get_renderer().render_texture(node, None)
        tex.save_to_png(out)
        loop.quit()
        return False

    GLib.timeout_add(500, snap)
    loop.run()


if __name__ == "__main__":
    main()
