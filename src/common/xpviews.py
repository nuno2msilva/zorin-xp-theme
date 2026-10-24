"""XP's folder views — Miniaturas, Mosaicos, Ícones, Lista and Detalhes — as
rules shared by the Explorer (Nautilus, src/nautilus-xp) and the Open, Save
and Browse for Folder dialogs (src/filechooser): kept in one place, so a
change here changes both. tools/build.py also writes some of them into the
GTK theme's Explorer CSS ({{view:NAME}} in src/gtk/*.css.in).

Positions are in pixels from the top-left of the view's white area,
measured in XP captures. Plain Python (no GTK): each side measures text
with its own toolkit and passes a measure(text) -> width function.
"""

import math

VIEWS = ('thumbnails', 'tiles', 'icons', 'list', 'details')

# Tahoma 8 as XP draws it: 13 px lines, the baseline 11 px below their top
LINE = 13
ASCENT = 11

HIGHLIGHT = (0x31, 0x6A, 0xC5)      # the selected name; icons blended halfway to it
FACE = (0xEC, 0xE9, 0xD8)           # selection without the focus; thumbnails' frame
GREY = (0x80, 0x80, 0x80)           # Tiles' captions
SORTED_BG = (0xF7, 0xF7, 0xF7)      # Details: the column the list is sorted by


def css_colour(rgb):
    return '#%02X%02X%02X' % tuple(rgb)


# ------------------------------------------------------------------ grids
# The first item at ORIGIN, the next ones every PITCH (columns as many as fit
# in the view's width minus ORIGIN_X on each side; the leftover stays on
# the right).
ORIGIN_X, ORIGIN_Y = 4, 2
PITCH = {'thumbnails': (125, 139), 'tiles': (218, 56), 'icons': (75, 75)}
# inside an item: the icon (Icons, Tiles) and the thumbnail's frame
ICON_SIZE = {'thumbnails': 48, 'tiles': 48, 'icons': 32, 'list': 16, 'details': 16}
ICON_AT = {'icons': (21, 4), 'tiles': (1, 4)}
THUMB_FRAME = 96                    # 1 px FACE over the image's edge; selected: 3 px outside
THUMB_AT = (14, 6)
# XP's icons stop at 48 px: in Thumbnails other files get it in the frame's
# centre, only images get a thumbnail (fitted to 96, then 94 x 94 inside)
THUMB_ICON = 48

# The name: Icons and Thumbnails centred below the icon, NAME_WIDTH wide, its
# first line at NAME_TOP; Tiles beside the icon at TILE_TEXT_X, centred on
# the item's height 1 px above the middle, with the captions below it
NAME_WIDTH = {'thumbnails': PITCH['thumbnails'][0] - 4, 'icons': PITCH['icons'][0] - 4, 'tiles': 158}
NAME_TOP = {'icons': 40, 'thumbnails': 106}
TILE_TEXT_X = 54


def name_x(view, text_w, line_w=None):
    """Icons, Thumbnails: where the name (text_w: its widest line) starts in
    the item, or one of its lines (line_w). Centred as the Explorer lays it
    out: the item's content (the icon or the frame, and the name) in the
    item less 2 px on each side, then the name in the content (the odd pixel
    on the right), then each line in the name (the odd pixel on the left)."""
    art = THUMB_FRAME if view == 'thumbnails' else ICON_SIZE[view]
    content = max(art, text_w)
    x = (PITCH[view][0] - 4 - content) // 2 + 2 + (content - text_w) // 2
    return x if line_w is None else x + (text_w - line_w + 1) // 2


def full_name_x(view, cut_w, full_w):
    """Icons, Thumbnails: where the whole name (its widest line full_w) starts
    when it goes over the items below — centred on the cut name (cut_w), the
    half pixel to the right, as the Explorer places it. Its lines are
    centred in it as name_x's."""
    return math.floor(name_x(view, cut_w) + cut_w / 2 - (full_w + 4) / 2 + 0.5) + 2


def tile_text_top(lines):
    """Tiles: the top of the name's first line in the item, for `lines` lines
    of text (name and captions)."""
    return (PITCH['tiles'][1] - LINE * lines) // 2 - 1


def name_lines(view, is_dir):
    """How a name is cut in a grid: (lines, split, strip) for xp_wrap.
    Icons and Thumbnails: up to 2 lines. Tiles: a folder up to 2 (nothing
    below it), a file 1 (type and size below), long words broken where the
    line ends and the space before "..." kept (as XP's, measured)."""
    if view == 'tiles':
        return (2 if is_dir else 1), True, False
    return 2, False, True


def full_name(focused, selected):
    """Icons and Thumbnails: the whole name (going over the items below it,
    never moving them) only for the item with the focus while it is selected
    and the view has the focus; every other name stays cut."""
    return focused and selected


def tile_captions(is_dir, kind, size, dims=''):
    """Tiles: what goes below the name — images their dimensions and type,
    other files the type and size, folders nothing."""
    if is_dir:
        return []
    return [dims, kind] if dims else [kind, size]


def kb_size(n, thousands='.'):
    """A size as XP's Details and Tiles show it: in KB, rounded up, with a
    thousands separator ("0 KB" only for an empty file)."""
    kb = (n + 1023) // 1024
    return f'{kb:,}'.replace(',', thousands)


DATE_FORMAT = '%d-%m-%Y %H:%M'      # Details (the pt-PT short date of XP)

# ------------------------------------------------------------------ List
# the grid on its side: columns filled from top to bottom, LIST_ROW high, all
# as wide as the folder's longest name (LIST_TEXT_X + name + LIST_GAP);
# LIST_PAD before the first one (the user's wish: XP starts at the edge, here
# as Details' icon); scrolled sideways, the wheel one column per notch
LIST_ROW = 17
LIST_TEXT_X = 18
LIST_GAP = 8
LIST_PAD = 4

# ------------------------------------------------------------------ Details
DETAILS_PAD = 4                     # before the first column (and the name's icon)
DETAILS_ROW = 17
DETAILS_TEXT_X = 22                 # the name, from the column's edge (icon at 0)
COLUMN_PAD = 6                      # the other columns' text, from each side
COLUMN_WIDTHS = {'name': 179, 'size': 97, 'type': 119, 'date': 121}
RIGHT_ALIGNED = ('size',)

# ------------------------------------------------------------------ renaming
# the box over the name (measured in XP): EDIT_H high (the 13 px line, 1 px
# and the outline, above and below), the text where the name was; before and
# after the text: Icons/Thumbnails EDIT_PAD on each side, centred on the
# item and growing on both sides up to EDIT_TEXT_W of text, then with more
# lines (4 + 13 px each); Tiles 4 and 15; List and Details 2 (so it does not
# touch the icon; XP 4) and 15
EDIT_H = 17
EDIT_LINE = LINE
EDIT_TEXT_W = 66
EDIT_PAD = 5
EDIT_SIDES = {'icons': (EDIT_PAD, EDIT_PAD), 'thumbnails': (EDIT_PAD, EDIT_PAD), 'tiles': (4, 15),
              'list': (2, 15), 'details': (2, 15)}


def edit_box(view, text_w, lines=1):
    """The rename box's size for a text text_w wide (lines: its lines when
    wrapped at EDIT_TEXT_W, Icons and Thumbnails)."""
    before, after = EDIT_SIDES[view]
    if view in NAME_TOP and text_w > EDIT_TEXT_W:
        return EDIT_TEXT_W + before + after + 2, 4 + EDIT_LINE * lines
    return text_w + before + after + 2, EDIT_H


# ------------------------------------------------------------------ text
def xp_wrap(text, width, measure, lines=2, split=False, strip=True):
    """text in up to `lines` lines of `width` px, like XP's DrawText with
    DT_WORDBREAK | DT_END_ELLIPSIS: breaks at spaces; a word wider than the
    line is cut with "..." and ends there; the last line takes the rest of
    the text, cut at the end. lines=None: the whole text (the focused item's
    name in XP), with long words broken where the line ends. split: long
    words broken where the line ends with a line limit too (XP's Tiles);
    strip=False: a space before the "..." stays (also Tiles)."""
    if measure(text) <= width:
        return text

    def fits(t):                        # the longest start of t that fits (>= 1)
        lo, hi = 1, len(t)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if measure(t[:mid]) <= width:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def cut(t):
        if measure(t) <= width:
            return t
        lo, hi = 0, len(t)

        def start(n):
            return t[:n].rstrip() if strip else t[:n]
        while lo < hi:                  # the longest start that fits with "..."
            mid = (lo + hi + 1) // 2
            if measure(start(mid) + '...') <= width:
                lo = mid
            else:
                hi = mid - 1
        return start(lo) + '...'
    out = []
    rest = text
    while rest and (lines is None or len(out) < lines):
        if lines is not None and len(out) == lines - 1:
            out.append(cut(rest))
            break
        words = rest.split(' ')
        line = words[0]
        if measure(line) > width:
            if lines is None or split:
                n = fits(line)
                out.append(line[:n])
                rest = rest[n:]
                continue
            out.append(cut(line))
            break
        i = 1
        while i < len(words) and measure(line + ' ' + words[i]) <= width:
            line += ' ' + words[i]
            i += 1
        out.append(line)
        rest = ' '.join(words[i:])
    return '\n'.join(out)


def cut_line(text, width, measure):
    """One line cut with "..." (Details' columns, List never cuts)."""
    return xp_wrap(text, width, measure, 1)


# ------------------------------------------------------------------ CSS
def css_values():
    """The numbers the theme's Explorer CSS takes from here ({{view:NAME}}).
    Nautilus puts an item's icon (and the thumbnail's frame) at the top of
    its cell: the grid's top padding is where XP has the icon."""
    return {
        'GRID_TOP_ICONS': ORIGIN_Y + ICON_AT['icons'][1],
        'GRID_TOP_TILES': ORIGIN_Y + ICON_AT['tiles'][1],
        'GRID_TOP_THUMBS': ORIGIN_Y + THUMB_AT[1],
        'GRID_SIDE': ORIGIN_X,
        'TILE_W': PITCH['tiles'][0], 'TILE_H': PITCH['tiles'][1],
        'THUMB_H': PITCH['thumbnails'][1], 'ICON_H': PITCH['icons'][1],
        'LINE': LINE,
        'LIST_ROW': LIST_ROW, 'LIST_PAD': LIST_PAD, 'LIST_NAME_GAP': LIST_TEXT_X - ICON_SIZE['list'],
        'DETAILS_PAD': DETAILS_PAD, 'DETAILS_ROW': DETAILS_ROW, 'COLUMN_PAD': COLUMN_PAD,
        'GREY': css_colour(GREY), 'FACE': css_colour(FACE),
    }
