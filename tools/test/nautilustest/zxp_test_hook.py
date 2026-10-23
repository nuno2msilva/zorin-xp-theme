"""Only for the test Nautilus (tools/test/nautilustest/run.sh; not installed).

Broadway does not read the GNOME settings: the user's theme, icons and font
are set here. And a channel to run Python inside Nautilus (like Marionette
in Zen): the code written to $ZXP_TEST_RPC/in.py runs and what it prints
goes to out.txt; shot(path) draws the window into a PNG.
"""
import faulthandler
import io
import os
import signal
import traceback

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Gsk', '4.0')
gi.require_version('Graphene', '1.0')
from gi.repository import Gdk, Gio, GLib, Graphene, Gsk, Gtk  # noqa: E402

RPC = os.environ.get('ZXP_TEST_RPC')
# kill -USR1 <pid>: where Python is (for when Nautilus gets stuck)
if RPC:
    os.makedirs(RPC, exist_ok=True)
    _stacks = open(os.path.join(RPC, 'stacks.txt'), 'a')
    faulthandler.register(signal.SIGUSR1, file=_stacks, all_threads=True)

settings = Gtk.Settings.get_default()
if settings is not None:
    for key, value in (('gtk-theme-name', 'WindowsXP-Luna'), ('gtk-icon-theme-name', 'WindowsXP'),
                       ('gtk-font-name', 'Tahoma 8.25'), ('gtk-cursor-theme-name', 'WindowsXP-Cursors'),
                       # (without this Broadway stays at -1 and libadwaita's "sp" become 0 px)
                       ('gtk-xft-dpi', 96 * 1024)):
        settings.set_property(key, value)


def window():
    app = Gio.Application.get_default()
    wins = [w for w in app.get_windows() if w.__gtype__.name == 'NautilusWindow']
    return app.get_active_window() if app.get_active_window() in wins else (wins[0] if wins else None)


_renderer = None


def shot(path, widget=None):
    """Draws the window (or a widget) into a PNG, at real size. (A single
    renderer, never freed: GTK aborts if an active renderer is freed.)"""
    global _renderer
    w = widget or window()
    width, height = w.get_width(), w.get_height()
    paintable = Gtk.WidgetPaintable.new(w)
    snap = Gtk.Snapshot()
    paintable.snapshot(snap, width, height)
    node = snap.to_node()
    if node is None:
        return None
    if _renderer is None:
        _renderer = Gsk.CairoRenderer.new()
        _renderer.realize_for_display(Gdk.Display.get_default())
    rect = Graphene.Rect()
    rect.init(0, 0, width, height)
    _renderer.render_texture(node, rect).save_to_png(path)
    return (width, height)


def walk(widget):
    yield widget
    child = widget.get_first_child()
    while child:
        yield from walk(child)
        child = child.get_next_sibling()


def poll():
    src = os.path.join(RPC, 'in.py')
    if os.path.exists(src):
        code = open(src).read()
        os.remove(src)
        out = io.StringIO()
        env = {'Gtk': Gtk, 'Gdk': Gdk, 'Gio': Gio, 'GLib': GLib, 'window': window, 'shot': shot,
               'walk': walk, 'print': lambda *a: out.write(' '.join(map(str, a)) + '\n')}
        try:
            exec(code, env)
        except Exception:
            out.write(traceback.format_exc())
        tmp = os.path.join(RPC, 'out.tmp')
        with open(tmp, 'w') as f:
            f.write(out.getvalue())
        os.rename(tmp, os.path.join(RPC, 'out.txt'))
    return True


if RPC:
    os.makedirs(RPC, exist_ok=True)
    GLib.timeout_add(150, poll)
