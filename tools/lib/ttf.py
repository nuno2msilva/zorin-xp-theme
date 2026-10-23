"""Minimal reading of TrueType files (the tables, no dependencies).

  t = tables("tahoma.ttf")         {"head": bytes, "OS/2": bytes, ...}
  gdi_ascent_descent(t, 19)        GDI's (tmAscent, tmDescent) at that size
"""
import struct


def tables(path):
    """{tag: bytes} of every table in the file."""
    with open(path, "rb") as f:
        data = f.read()
    n, = struct.unpack_from(">H", data, 4)
    out = {}
    for i in range(n):
        tag, _sum, off, ln = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        out[tag.decode("latin-1")] = data[off:off + ln]
    return out


def gdi_ascent_descent(t, px):
    """The ascent and descent GDI gives the font (tmAscent/tmDescent): the
    Windows metrics of the OS/2 table (usWinAscent/usWinDescent), scaled."""
    upem, = struct.unpack_from(">H", t["head"], 18)
    win_asc, win_desc = struct.unpack_from(">HH", t["OS/2"], 74)
    return round(win_asc * px / upem), round(win_desc * px / upem)
