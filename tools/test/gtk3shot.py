#!/usr/bin/env python3
"""Desenha uma galeria de widgets GTK3 fora do ecrã e grava em PNG.

Uso: GTK_THEME=<tema> XDG_DATA_HOME=<dir> gtk3shot.py <saida.png> [css-extra]
"""
import sys

import gi
import os

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402


def gallery():
    grid = Gtk.Grid(column_spacing=8, row_spacing=8, margin=8)
    r = 0

    def row(*ws):
        nonlocal r
        for c, w in enumerate(ws):
            grid.attach(w, c, r, 1, 1)
        r += 1

    b_def = Gtk.Button(label="OK")
    b_def.set_can_default(True)
    b_def.get_style_context().add_class("default")
    b_dis = Gtk.Button(label="Cancelar")
    b_dis.set_sensitive(False)
    tog = Gtk.ToggleButton(label="Alternar")
    tog.set_active(True)
    row(Gtk.Button(label="Aplicar"), b_def, b_dis, tog)

    c1 = Gtk.CheckButton(label="Opção")
    c2 = Gtk.CheckButton(label="Marcada")
    c2.set_active(True)
    c3 = Gtk.CheckButton(label="Mista")
    c3.set_inconsistent(True)
    c4 = Gtk.CheckButton(label="Desativada")
    c4.set_active(True)
    c4.set_sensitive(False)
    row(c1, c2, c3, c4)

    r1 = Gtk.RadioButton(label="Rádio A")
    r2 = Gtk.RadioButton.new_with_label_from_widget(r1, "Rádio B")
    r2.set_active(True)
    r3 = Gtk.RadioButton(label="Desativado")
    r3.set_sensitive(False)
    e = Gtk.Entry(text="Texto")
    row(r1, r2, r3, e)

    combo = Gtk.ComboBoxText()
    for t in ("Windows XP", "Clássico"):
        combo.append_text(t)
    combo.set_active(0)
    ecombo = Gtk.ComboBoxText.new_with_entry()
    ecombo.append_text("Editável")
    ecombo.set_active(0)
    spin = Gtk.SpinButton.new_with_range(0, 100, 1)
    spin.set_value(42)
    e2 = Gtk.Entry(text="Desativado")
    e2.set_sensitive(False)
    row(combo, ecombo, spin, e2)

    pb = Gtk.ProgressBar()
    pb.set_fraction(0.6)
    sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    sc.set_value(30)
    sc.set_draw_value(False)
    sc.set_size_request(120, -1)
    sw = Gtk.Switch()
    sw.set_active(True)
    row(pb, sc, sw, Gtk.Label(label="Etiqueta"))

    nb = Gtk.Notebook()
    for t in ("Temas", "Ambiente de trabalho", "Aspeto"):
        nb.append_page(Gtk.Label(label=f"Conteúdo de {t}"), Gtk.Label(label=t))
    nb.set_size_request(300, 90)
    grid.attach(nb, 0, r, 2, 2)

    fr = Gtk.Frame(label="Grupo")
    fr.add(Gtk.Label(label="dentro do grupo"))
    grid.attach(fr, 2, r, 2, 1)

    store = Gtk.ListStore(str, str)
    for i in range(12):
        store.append([f"Ficheiro {i}.txt", f"{i * 3} KB"])
    tv = Gtk.TreeView(model=store)
    for i, t in enumerate(("Nome", "Tamanho")):
        tv.append_column(Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i))
    tv.get_selection().select_path(Gtk.TreePath(2))
    scw = Gtk.ScrolledWindow()
    scw.set_shadow_type(Gtk.ShadowType.IN)
    scw.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
    scw.add(tv)
    scw.set_size_request(220, 110)
    grid.attach(scw, 2, r + 1, 2, 2)
    r += 3

    mb = Gtk.MenuBar()
    for t in ("Ficheiro", "Editar", "Ver", "Ajuda"):
        mb.append(Gtk.MenuItem(label=t))
    grid.attach(mb, 0, r, 2, 1)
    tb = Gtk.Toolbar()
    for t in ("Anterior", "Seguinte"):
        tb.insert(Gtk.ToolButton(label=t, icon_name="go-previous"), -1)
    grid.attach(tb, 0, r + 1, 2, 1)
    return grid


def main():
    out = sys.argv[1]
    s = Gtk.Settings.get_default()
    s.set_property("gtk-font-name", "Tahoma 8.25")
    s.set_property("gtk-xft-hintstyle", "hintfull")
    s.set_property("gtk-xft-antialias", 1)
    s.set_property("gtk-xft-rgba", "none")
    s.set_property("gtk-xft-dpi", 96 * 1024)
    if len(sys.argv) > 2:
        prov = Gtk.CssProvider()
        prov.load_from_path(sys.argv[2])
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, 900)
    win = Gtk.OffscreenWindow()
    win.add(gallery())
    win.show_all()

    def snap():
        pix = win.get_pixbuf()
        pix.savev(out, "png", [], [])
        Gtk.main_quit()
        return False

    GLib.timeout_add(400, snap)
    Gtk.main()


if __name__ == "__main__":
    main()
