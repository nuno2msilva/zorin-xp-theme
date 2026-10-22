"""Menus dos binários do Windows (RT_MENU), com o id de cada item.

parse(dados) -> [{"id": int ou None, "text": str, "flags": int,
                  "items": [...] (só nos submenus)}]
O id de cada comando é o mesmo em todas as línguas do XP: é por ele que se
escolhem os itens (o texto muda com a língua). Separadores: text "" e id 0.
"""
import struct

MF_POPUP = 0x10
MF_END = 0x80


def _sz(d, o):
    e = o
    while struct.unpack_from("<H", d, e)[0]:
        e += 2
    return d[o:e].decode("utf-16le"), e + 2


def _parse_std(d, o):
    items = []
    while o < len(d):
        flags, = struct.unpack_from("<H", d, o)
        o += 2
        if flags & MF_POPUP:
            text, o = _sz(d, o)
            sub, o = _parse_std(d, o)
            items.append({"id": None, "text": text, "flags": flags, "items": sub})
        else:
            mid, = struct.unpack_from("<H", d, o)
            text, o = _sz(d, o + 2)
            items.append({"id": mid, "text": text, "flags": flags})
        if flags & MF_END:
            break
    return items, o


def _parse_ex(d, o):
    items = []
    while o < len(d):
        _type, _state, mid, flags = struct.unpack_from("<IIIH", d, o)
        text, o = _sz(d, o + 14)
        o = (o + 3) & ~3
        item = {"id": mid, "text": text, "flags": flags}
        if flags & 0x01:                       # submenu: dwHelpId e os itens
            o += 4
            item["items"], o = _parse_ex(d, o)
        items.append(item)
        if flags & MF_END:
            break
    return items, o


def parse(data):
    version, offset = struct.unpack_from("<HH", data, 0)
    if version == 1:                           # MENUEX
        return _parse_ex(data, 4 + offset)[0]
    return _parse_std(data, 4)[0]


def flat(items):
    """Todos os itens, pela ordem (os submenus antes dos seus itens)."""
    for it in items:
        yield it
        yield from flat(it.get("items", []))
