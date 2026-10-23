"""Reading dialog templates (RT_DIALOG, DIALOGEX) from XP binaries.

dialog(pe, id) -> {"title", "font", "size": (w, h) in DLU, "style",
                   "controls": [{"cls", "id", "text", "x", "y", "w", "h", "style"}]}
The measurements are in dialog units (DLU); with MS Shell Dlg / Tahoma 8 at
96 dpi: x * 1.5 and y * 1.625 px (rounded like MapDialogRect).
"""
import struct

CLASSES = {0x80: "Button", 0x81: "Edit", 0x82: "Static", 0x83: "ListBox",
           0x84: "ScrollBar", 0x85: "ComboBox"}


def _sz_or_ord(d, o):
    w, = struct.unpack_from("<H", d, o)
    if w == 0xFFFF:
        return struct.unpack_from("<H", d, o + 2)[0], o + 4
    e = o
    while struct.unpack_from("<H", d, e)[0]:
        e += 2
    return d[o:e].decode("utf-16le"), e + 2


def _align4(o):
    return (o + 3) & ~3


def dialog(pe, rid):
    d = pe.get(5, rid)
    ver, sig = struct.unpack_from("<HH", d, 0)
    if not (ver == 1 and sig == 0xFFFF):
        raise ValueError("só DIALOGEX")
    _help, _ex, style, n, x, y, cx, cy = struct.unpack_from("<IIIHhhhh", d, 4)
    o = 26
    _menu, o = _sz_or_ord(d, o)
    _cls, o = _sz_or_ord(d, o)
    title, o = _sz_or_ord(d, o)
    font = None
    if style & 0x40 or style & 0x48:          # DS_SETFONT / DS_SHELLFONT
        pt, weight, italic, _cs = struct.unpack_from("<HHBB", d, o)
        o += 6
        face, o = _sz_or_ord(d, o)
        font = (face, pt, weight, italic)
    controls = []
    for _ in range(n):
        o = _align4(o)
        _hid, _exs, cstyle, cxp, cyp, ccx, ccy, cid = struct.unpack_from("<IIIhhhhI", d, o)
        o += 24
        cls, o = _sz_or_ord(d, o)
        text, o = _sz_or_ord(d, o)
        extra, = struct.unpack_from("<H", d, o)
        o += 2 + extra
        controls.append({"cls": CLASSES.get(cls, cls), "id": cid, "text": text,
                         "x": cxp, "y": cyp, "w": ccx, "h": ccy, "style": cstyle})
    return {"title": title, "font": font, "size": (cx, cy), "style": style, "controls": controls}


def px(v, axis):
    """DLU -> px for Tahoma 8 at 96 dpi (base 6x13: x*6/4, y*13/8)."""
    return (v * 6 + 2) // 4 if axis == "x" else (v * 13 + 4) // 8
