# (for nt.py) loads the GTK4 theme from build/ on top of the installed one
import builtins, os
path = os.path.expanduser("~/Os meus documentos/Projects/Zorin XP/build/gtk/WindowsXP-Luna/gtk-4.0/gtk.css")
old = getattr(builtins, "_zxp_theme", None)
if old:
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), old)
for p in (getattr(builtins, "_zxp_css", None),):
    if p:
        Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), p)
        builtins._zxp_css = None
prov = Gtk.CssProvider()
prov.load_from_path(path)
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov, 900)
builtins._zxp_theme = prov
print("tema de build carregado")
