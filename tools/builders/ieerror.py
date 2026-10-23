"""IE6's "A página não pode ser apresentada" page for Zen's network error
page (src/zen-ie/content.css).

Firefox's error page only accepts chrome: resources (CSP), so no images:
everything is CSS that loads nothing. The text and the images are those of
XP's own DNSERROR.HTM (an HTML resource of shdoclc.dll, in pt-PT, with
pagerror.gif, refresh.gif, search.gif and back.gif from the same DLL):

  - the page is laid out here as IE6 draws it (table with cellspacing 5 and
    cellpadding 3, IE's margins, line breaking with GDI's widths);
  - the text goes in two blocks (black, and red for the links), each one in a
    pseudo-element with the "ZXP Verdana IE" font (tools/lib/pixelfont.py mix):
    XP's Verdana in pixels, with the bold and the 13 pt heading in private
    codes and a 1 px space to put each line at its x; the lines are 1 px
    high, so that each one sits at its y;
  - the images and the list bullets are box-shadows of 1 px per pixel;
  - the rule and the links' underlines are gradients.

css(widths) -> {"text", "links", "icons", "background", "detect"}
(the page and the images come from assets: locales/<language>/ie/dnserror.htm
and images/ie/*.gif)
"""
import html.parser
import io
import re

from PIL import Image
import os
import sys

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOLD, BIG, SPACER = 0xE000, 0xE400, 0xF8F0
LINE, H1_LINE = 15, 20               # 8/11 pt e 13/15 pt a 96 ppp
BASE, H1_BASE = 12, 16               # baseline within the line
LAYER_BASE = 4                       # in the 1 px lines of the 11 px font (measured)
BODY_X, BODY_Y = 10, 15              # margens do <body> do IE
SPACING, PADDING = 5, 3              # of the <table>
TABLE_W = 400
H1_MARGIN, P_MARGIN, HR_MARGIN, UL_INDENT = 11, 12, 6, 40
DISC = [".###.", "#####", "#####", "#####", ".###."]


class _Events(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []

    def handle_starttag(self, tag, attrs):
        self.events.append(("start", tag, dict(attrs)))

    def handle_endtag(self, tag):
        self.events.append(("end", tag, None))

    def handle_data(self, data):
        self.events.append(("text", data, None))


def _blocks(page):
    """[(type, [items])]: items = ("w", text, style) | ("s", style) |
    ("img", name, alignment, link) | ("br",); style: "n", "b" or "a"."""
    p = _Events()
    p.feed(page)
    blocks, cur = [], None
    bold = link = skip = 0
    cells = 0

    def new(kind):
        nonlocal cur
        cur = (kind, [])
        blocks.append(cur)

    for ev, a, attrs in p.events:
        if ev == "start":
            if a in ("script", "head", "object", "style", "title"):
                skip += 1
            elif a == "td":
                cells += 1
                if cells == 3:                  # the first wide cell: the paragraph
                    new("p")
            elif a in ("h1", "h2", "p", "li"):
                new(a)
            elif a == "hr":
                new("hr")
                cur = None
            elif a == "b":
                bold += 1
            elif a == "a" and "href" in attrs:
                link += 1
            elif a == "img" and cur is not None:
                cur[1].append(("img", attrs.get("src", "").lower(), (attrs.get("align") or "").lower(), link > 0))
            elif a == "br" and cur is not None:
                cur[1].append(("br",))
        elif ev == "end":
            if a in ("script", "head", "object", "style", "title"):
                skip = max(0, skip - 1)
            elif a == "b":
                bold = max(0, bold - 1)
            elif a == "a" and link:
                link -= 1
            elif a in ("h1", "h2", "p", "li", "td"):
                cur = None
        elif not skip and cur is not None:
            style = "a" if link else ("b" if bold else "n")
            for part in re.split(r"(\s+)", a):
                if part:
                    cur[1].append(("s", style) if part.isspace() else ("w", part, style))
    return [b for b in blocks if b[0] == "hr" or any(i[0] != "s" for i in b[1])]


class _Layout:
    def __init__(self, widths, images):
        self.w = widths
        self.images = images
        self.text = {}          # baseline y -> [(x, text, style)]
        self.links = {}
        self.icons = []         # (x, y, nome)
        self.discs = []
        self.rules = []         # (x, y, width, height, colour)
        self.detect = None      # the "Detectar definições de rede" link

    def adv(self, s, style):
        table = self.w["h" if style == "h" else ("b" if style == "b" else "n")]
        return sum(table.get(str(ord(c)), table["32"]) for c in s)

    def flow(self, items, x0, width, top, big=False):
        """Lays the items out in lines starting at (x0, top); returns the next y."""
        line_h, base = (H1_LINE, H1_BASE) if big else (LINE, BASE)
        # words: what follows without a space (a bold part and the comma after it,
        # an image and the text) is not split when breaking the line
        words, cur, gap = [], [], None
        for it in items:
            if it[0] == "br":
                if cur:
                    words.append((gap, cur))
                words.append(("br", None))
                cur, gap = [], None
            elif it[0] == "s":
                if cur:
                    words.append((gap, cur))
                    cur = []
                gap = it[1]
            else:
                if it[0] == "img":
                    cur.append(("img", it, self.images[it[1]].width))
                else:
                    cur.append(("w", it, self.adv(it[1], "h" if big else it[2])))
        if cur:
            words.append((gap, cur))

        lines, line, w = [], [], 0
        for gap, pieces in words:
            if gap == "br":
                lines.append(line)
                line, w = [], 0
                continue
            ww = sum(p[2] for p in pieces)
            sw = self.adv(" ", "h" if big else gap) if gap and line else 0
            if line and w + sw + ww > width:
                lines.append(line)
                line, w, sw = [], 0, 0
            if sw:
                line.append(("s", gap, sw))
                w += sw
            line += pieces
            w += ww
        if line:
            lines.append(line)

        y = top
        for ln in lines:
            above, below = base, line_h - base
            for kind, it, _w in ln:
                if kind == "img":
                    h = self.images[it[1]].height
                    a, b = (h // 2, h - h // 2) if it[2] in ("middle", "center", "absmiddle") else (h, 0)
                    above, below = max(above, a), max(below, b)
            baseline = y + above
            x = x0
            link_x = None
            for kind, it, pw in ln:
                if kind == "img":
                    im = self.images[it[1]]
                    mid = it[2] in ("middle", "center", "absmiddle")
                    self.icons.append((x, baseline - (im.height // 2 if mid else im.height), it[1]))
                    if it[3] and link_x is None:
                        link_x = x
                else:
                    text, style = (" ", it) if kind == "s" else (it[1], it[2])
                    if style == "a":
                        self.links.setdefault(baseline, []).append((x, text, "n"))
                        self.rules.append((x, baseline + 1, pw, 1, "#f00"))
                        if link_x is None:
                            link_x = x
                        if kind == "w" and ("Detectar" in text or self.detect and self.detect[1] == y):
                            start = self.detect[0] if self.detect else link_x
                            self.detect = (start, y, x + pw - start, above + below)
                    else:
                        self.text.setdefault(baseline, []).append((x, text, "h" if big else style))
                x += pw
            y += above + below
        return y


def css(widths):
    from lib import assets
    page = assets.locale_file("ie/dnserror.htm").decode("cp1252")
    images = {name: Image.open(io.BytesIO(assets.image_file(f"ie/{name}"))).convert("RGBA")
              for name in ("pagerror.gif", "refresh.gif", "search.gif", "back.gif")}
    lay = _Layout(widths, images)
    blocks = _blocks(page)

    # first table row: the icon and the title (cell aligned to the middle)
    top = BODY_Y + SPACING
    icon = images["pagerror.gif"]
    icon_cell = icon.width + 2 * PADDING
    title_x = BODY_X + SPACING + icon_cell + SPACING + PADDING
    title_w = TABLE_W - 3 * SPACING - icon_cell - 2 * PADDING
    full_x = BODY_X + SPACING + PADDING
    full_w = TABLE_W - 2 * SPACING - 2 * PADDING
    h1 = next(b for b in blocks if b[0] == "h1")
    h1_h = _Layout(widths, images).flow(h1[1], 0, title_w, 0, big=True) + 2 * H1_MARGIN
    row = max(icon.height, h1_h)
    lay.icons.append((full_x, top + PADDING, "pagerror.gif"))
    lay.flow(h1[1], title_x, title_w, top + PADDING + (row - h1_h) // 2 + H1_MARGIN, big=True)
    top += row + 2 * PADDING + SPACING

    # second row: the paragraph; third: the rule, "Experimente o seguinte:", the list...
    rest = [b for b in blocks if b[0] != "h1"]
    y = lay.flow(rest.pop(0)[1], full_x, full_w, top + PADDING)
    y += PADDING + SPACING + PADDING
    first = True
    margin = 0                          # pending bottom margin (margins collapse)
    in_list = False
    for kind, items in rest:
        if kind == "hr":
            y += 0 if first else max(margin, HR_MARGIN)
            lay.rules.append((full_x, y, full_w, 2, "#c0c0c0"))
            y += 2
            margin = HR_MARGIN
        elif kind == "li":
            if not in_list:
                y += max(margin, P_MARGIN)
                in_list = True
            x = full_x + UL_INDENT
            lay.discs.append((x - 13, y + 5))
            y = lay.flow(items, x, full_w - UL_INDENT, y)
            margin = P_MARGIN
        else:
            in_list = False
            y += max(margin, P_MARGIN)
            y = lay.flow(items, full_x, full_w, y) if any(i[0] not in ("s", "br") for i in items) else y + LINE
            margin = P_MARGIN
        first = False

    def layer(lines):
        if not lines:
            return '""'
        rows = []
        for k in range(0, max(lines) - LAYER_BASE + 1):
            out, pen = [], 0
            for x, s, style in sorted(lines.get(k + LAYER_BASE, [])):
                if x > pen:
                    out.append(chr(SPACER) * (x - pen))
                    pen = x
                out += [chr(BOLD + ord(c)) if style == "b" else chr(BIG + ord(c)) if style == "h" else c
                        for c in s]
                pen += lay.adv(s, style)
            rows.append("".join(out))
        text = "\n".join(rows)
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\A ") + '"'

    shadows = []
    for x, y, name in lay.icons:
        im = images[name]
        for py in range(im.height):
            for px in range(im.width):
                r, g, b, a = im.getpixel((px, py))
                if a > 127:
                    shadows.append(f"{x + px + 1}px {y + py + 1}px #{r:02x}{g:02x}{b:02x}")
    for x, y in lay.discs:
        for dy, row in enumerate(DISC):
            for dx, c in enumerate(row):
                if c == "#":
                    shadows.append(f"{x + dx + 1}px {y + dy + 1}px #000")
    bg = [f"linear-gradient({c}, {c}) {x}px {y}px / {w}px {h}px no-repeat" for x, y, w, h, c in lay.rules]
    return {"text": layer(lay.text), "links": layer(lay.links), "icons": ", ".join(shadows),
            "background": ", ".join(bg), "detect": lay.detect}


if __name__ == "__main__":
    # (debugging) ieerror.py <widths.json>: the error page's CSS
    import json
    import sys
    r = css(json.load(open(sys.argv[1])))
    print(r["detect"], len(r["text"]), len(r["icons"]), r["background"][:300])
