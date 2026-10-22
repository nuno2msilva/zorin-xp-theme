"""A página "Não é possível apresentar a página" do IE6 para a página de erro
de rede do Zen (src/zen-ie/content.css).

A página de erro do Firefox só aceita recursos chrome: (CSP), por isso nada
de imagens: tudo é CSS que não carrega nada. O texto e as imagens são os do
próprio DNSERROR.HTM do XP (recurso HTML da shdoclc.dll, em pt-PT, com
pagerror.gif, refresh.gif, search.gif e back.gif da mesma DLL):

  - a página é disposta aqui como o IE6 a desenha (tabela com cellspacing 5 e
    cellpadding 3, margens do IE, quebra de linha com as larguras do GDI);
  - o texto vai em dois blocos (preto, e vermelho para as ligações), cada um
    num pseudo-elemento com a fonte "ZXP Verdana IE" (tools/lib/pixelfont.py mix):
    a Verdana do XP em píxeis, com o negrito e o título de 13 pt em códigos
    privados e um espaço de 1 px para pôr cada linha no seu x; as linhas
    têm 1 px de altura, para cada uma ficar no seu y;
  - as imagens e as marcas da lista são box-shadow de 1 px por píxel;
  - a linha e os sublinhados das ligações são gradientes.

css(widths) -> {"text", "links", "icons", "background", "detect"}
(a página e as imagens vêm de assets: locales/<língua>/ie/dnserror.htm e
images/ie/*.gif)
"""
import html.parser
import io
import re

from PIL import Image
import os
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOLD, BIG, SPACER = 0xE000, 0xE400, 0xF8F0
LINE, H1_LINE = 15, 20               # 8/11 pt e 13/15 pt a 96 ppp
BASE, H1_BASE = 12, 16               # linha de base dentro da linha
LAYER_BASE = 4                       # nas linhas de 1 px da fonte de 11 px (medido)
BODY_X, BODY_Y = 10, 15              # margens do <body> do IE
SPACING, PADDING = 5, 3              # da <table>
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
    """[(tipo, [itens])]: itens = ("w", texto, estilo) | ("s", estilo) |
    ("img", nome, alinhamento, ligação) | ("br",); estilo: "n", "b" ou "a"."""
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
                if cells == 3:                  # a primeira célula larga: o parágrafo
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
        self.text = {}          # y da linha de base -> [(x, texto, estilo)]
        self.links = {}
        self.icons = []         # (x, y, nome)
        self.discs = []
        self.rules = []         # (x, y, largura, altura, cor)
        self.detect = None      # a ligação "Detectar definições de rede"

    def adv(self, s, style):
        table = self.w["h" if style == "h" else ("b" if style == "b" else "n")]
        return sum(table.get(str(ord(c)), table["32"]) for c in s)

    def flow(self, items, x0, width, top, big=False):
        """Dispõe os itens em linhas a partir de (x0, top); devolve o y a seguir."""
        line_h, base = (H1_LINE, H1_BASE) if big else (LINE, BASE)
        # palavras: o que vem seguido sem espaço (um negrito e a vírgula a seguir,
        # uma imagem e o texto) não se separa ao quebrar a linha
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

    # 1.ª linha da tabela: o ícone e o título (célula alinhada ao meio)
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

    # 2.ª linha: o parágrafo; 3.ª: a linha, "Experimente o seguinte:", a lista...
    rest = [b for b in blocks if b[0] != "h1"]
    y = lay.flow(rest.pop(0)[1], full_x, full_w, top + PADDING)
    y += PADDING + SPACING + PADDING
    first = True
    margin = 0                          # margem de baixo pendente (as margens colapsam)
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
    # (depuração) ieerror.py <larguras.json>: o CSS da página de erro
    import json
    import sys
    r = css(json.load(open(sys.argv[1])))
    print(r["detect"], len(r["text"]), len(r["icons"]), r["background"][:300])
