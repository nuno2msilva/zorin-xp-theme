"""Builds the GTK3/GTK4 themes from src/gtk/*.css.in and luna.msstyles."""
import os
import re
import shutil

from builders import gtkassets
from lib import msstyles
from lib.paths import ROOT
from lib import assets

SRC = os.path.join(ROOT, "src", "gtk")


def preprocess(text, target):
    """Keeps the /*@<target>*/ … /*@end*/ blocks and removes the other targets' ones."""
    out = []
    keep = True
    for line in text.splitlines(keepends=True):
        m = re.match(r"\s*/\*@(gtk3|gtk4|end)\*/\s*$", line)
        if m:
            keep = m.group(1) in ("end", target)
            continue
        if keep:
            out.append(line)
    text = "".join(out)
    # conditional blocks within a line: /*@gtk3*/ ... /*@end*/
    def inline(m):
        return m.group(2) if m.group(1) == target else ""
    return re.sub(r"/\*@(gtk3|gtk4)\*/(.*?)/\*@end\*/", inline, text, flags=re.S)


def _url(name, state, fill=False):
    return f'url("assets/{name}-{state}{"-fill" if fill else ""}.png")'


def substitute(text, info):
    def part(m):
        name, state = m.group(1), m.group(2)
        i = info[name]
        l, r, t, b = i["margins"]
        rep = "repeat" if i.get("tile") else "stretch"
        css = ("border-style: solid; border-width: 0; border-radius: 0; "
               f"border-image: {_url(name, state)} {t} {r} {b} {l} {rep}; "
               f"border-image-width: {t}px {r}px {b}px {l}px; background-color: transparent; ")
        if i.get("fill"):
            css += (f"background-image: {_url(name, state, True)}; "
                    "background-size: 100% 100%; background-repeat: no-repeat;")
        else:
            css += "background-image: none;"
        return css

    def state(m):
        name, st = m.group(1), m.group(2)
        css = f"border-image-source: {_url(name, st)};"
        if info[name].get("fill"):
            css += f" background-image: {_url(name, st, True)};"
        return css

    text = re.sub(r"\{\{part:([a-z0-9-]+):([a-z0-9-]+)\}\}", part, text)
    text = re.sub(r"\{\{state:([a-z0-9-]+):([a-z0-9-]+)\}\}", state, text)

    def tok(m):
        kind, name = m.group(1), m.group(2)
        if name not in info:
            raise KeyError(f"asset desconhecido no CSS: {name}")
        l, r, t, b = info[name]["margins"]
        if kind == "slice":
            return f"{t} {r} {b} {l}"
        if kind == "bw":
            return f"{t}px {r}px {b}px {l}px"
        raise KeyError(kind)
    return re.sub(r"\{\{(slice|bw):([a-z0-9-]+)\}\}", tok, text)


def build(out_dir, name="WindowsXP-Luna", theme_name="luna"):
    """GTK3/GTK4 themes in out_dir/<name>, with the pieces of the theme theme_name."""
    ms = assets.theme(theme_name)
    theme = os.path.join(out_dir, name)
    shared_assets = os.path.join(theme, "gtk-assets")
    info = gtkassets.export(ms, shared_assets, assets.fonts_dir())
    gtkassets.export_explorer(ms, shared_assets)
    sources = sorted(f for f in os.listdir(SRC) if f.endswith(".css.in"))
    for target, sub in (("gtk3", "gtk-3.0"), ("gtk4", "gtk-4.0")):
        d = os.path.join(theme, sub)
        os.makedirs(d, exist_ok=True)
        css = "".join(substitute(preprocess(open(os.path.join(SRC, f)).read(), target), info)
                      for f in sources)
        with open(os.path.join(d, "gtk.css"), "w") as f:
            f.write(css)
        # GTK3/GTK4 resolve url() relative to the CSS file
        link = os.path.join(d, "assets")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink("../gtk-assets", link)
    with open(os.path.join(theme, "index.theme"), "w") as f:
        f.write(f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={name}\n"
                "Comment=Windows XP Luna (Azul), gerado a partir do luna.msstyles\nEncoding=UTF-8\n\n"
                f"[X-GNOME-Metatheme]\nGtkTheme={name}\nMetacityTheme={name}\n"
                "IconTheme=WindowsXP\nCursorTheme=WindowsXP-Cursors\n"
                "ButtonLayout=icon:minimize,maximize,close\n")
    return theme
