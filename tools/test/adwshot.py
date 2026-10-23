#!/usr/bin/env python3
"""Captures a test libadwaita window with the installed theme.

Reproduces the structure of the zorin-taskbar preferences
(AdwPreferencesWindow with pages in the AdwViewSwitcher, rows with switches,
a slider with marks, an options button) to tune the CSS without opening the
real window.

Usage: adwshot.py <out.png> [width] [height] [backdrop]
"""
import sys

import gi
import os

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402


def page(title, icon):
    p = Adw.PreferencesPage(title=title, icon_name=icon)
    g = Adw.PreferencesGroup(title="Applications")
    for i, label in enumerate(("Show favorite applications", "Show running applications",
                               "Ungroup applications")):
        row = Adw.ActionRow(title=label)
        if i == 2:
            b = Gtk.Button(icon_name="emblem-system-symbolic", valign=Gtk.Align.CENTER)
            row.add_suffix(b)
        sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=i != 1)
        row.add_suffix(sw)
        g.add(row)
    p.add(g)
    g2 = Adw.PreferencesGroup(title="Panel style")
    row = Adw.ActionRow(title="Margin")
    sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 24, 1)
    sc.set_hexpand(True)
    sc.set_size_request(260, -1)
    for v in (4, 8, 12, 16, 24):
        sc.add_mark(v, Gtk.PositionType.TOP, str(v))
    row.add_suffix(sc)
    row.add_suffix(Gtk.Label(label="0 px"))
    g2.add(row)
    row = Adw.ActionRow(title="Panel background opacity (%)")
    row.add_suffix(Gtk.SpinButton.new_with_range(0, 100, 5))
    g2.add(row)
    p.add(g2)
    return p


PAGES = []


def xp_group_box(group):
    """The same as xpGroupBox in src/zorin-taskbar-xp/prefs.js."""
    inner = group.get_first_child()
    header = inner.get_first_child()
    content = header.get_next_sibling()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["zxp-groupbox"])
    if group.get_title():
        top = Gtk.Box()
        top.append(Gtk.Box(css_classes=["zxp-gb-tl"]))
        top.append(Gtk.Label(label=group.get_title(), css_classes=["zxp-gb-title"]))
        top.append(Gtk.Box(css_classes=["zxp-gb-tr"], hexpand=True))
        box.append(top)
    else:
        box.add_css_class("untitled")
    header.set_visible(False)
    inner.remove(content)
    content.add_css_class("zxp-gb-body")
    box.append(content)
    inner.append(box)


def main():
    out = sys.argv[1]
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 520
    app = Adw.Application(application_id="local.zxp.adwshot")

    def activate(_app):
        win = Adw.PreferencesWindow(application=app, title="Zorin Taskbar")
        win.set_search_enabled(True)
        for t, i in (("Style", "applications-graphics-symbolic"),
                     ("Position", "find-location-symbolic"),
                     ("Behavior", "preferences-system-symbolic"),
                     ("Action", "input-mouse-symbolic")):
            pg = page(t, i)
            PAGES.append(pg)
            win.add(pg)
        win.set_default_size(w, h)
        if len(sys.argv) > 4 and sys.argv[4] == "sheet":
            # the same as src/zorin-taskbar-xp/prefs.js
            for pg in PAGES:
                c = pg.get_first_child()
                while not isinstance(c, Adw.Clamp):
                    c = c.get_first_child()
                c.set_maximum_size(10000)
                c.set_tightening_threshold(10000)
                while c and not isinstance(c, Gtk.Box):
                    c = c.get_first_child()
                g = c.get_first_child()
                while g:
                    if isinstance(g, Adw.PreferencesGroup):
                        xp_group_box(g)
                    g = g.get_next_sibling()
            nb = Gtk.Notebook(margin_top=7, margin_bottom=6, margin_start=5, margin_end=6)
            for pg in list(PAGES):
                win.remove(pg)
                nb.append_page(pg, Gtk.Label(label=pg.get_title()))
            title = Gtk.Label(label=win.get_title(), css_classes=["title"], xalign=0)
            header = Adw.HeaderBar(title_widget=Adw.Bin())
            header.pack_start(title)
            view = Adw.ToolbarView(content=nb)
            view.add_top_bar(header)
            win.set_content(view)
            win.add_css_class("zxp-property-sheet")
        win.present()

        def snap():
            ww, hh = win.get_width(), win.get_height()
            paint = Gtk.WidgetPaintable.new(win)
            snapshot = Gtk.Snapshot()
            paint.snapshot(snapshot, ww, hh)
            tex = win.get_renderer().render_texture(snapshot.to_node(), None)
            tex.save_to_png(out)
            print(f"{ww}x{hh}")
            app.quit()
            return False

        GLib.timeout_add(700, snap)

    app.connect("activate", activate)
    app.run([])


if __name__ == "__main__":
    main()
