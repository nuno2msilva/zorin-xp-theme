"""Ícones do Windows: grupos de ícones das DLL/EXE (RT_GROUP_ICON /
RT_ICON) e ficheiros .ico (como os guarda tools/extract.py em assets/icons).

  group_icons(pe, id) / ico_icons(dados)  -> [(w, h, bpp, imagem RGBA)]
  best(pe, id, tam) / best_ico(dados, tam) -> a melhor imagem desse tamanho
  ico_file(pe, id)                         -> o grupo num ficheiro .ico
"""
import io
import struct

from PIL import Image

from lib import wincursor

RT_ICON = 3
RT_GROUP_ICON = 14


def _decode(entries):
    """[(w, h, bpp, dados)] -> [(w, h, bpp, Image RGBA)], por qualidade
    decrescente (as imagens que não se leem ficam de fora)."""
    out = []
    for w, h, bpp, data in entries:
        try:
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                img = Image.open(io.BytesIO(data)).convert("RGBA")
            else:
                img = wincursor.decode_dib_cursor(data)
        except Exception:
            continue
        out.append((w or 256, h or 256, bpp, img))
    out.sort(key=lambda e: (e[0], e[2]), reverse=True)
    return out


def _group_entries(pe, gid):
    """[(w, h, cores, planos, bpp, dados)] de um RT_GROUP_ICON."""
    g = pe.get(RT_GROUP_ICON, gid)
    if g is None:
        return []
    _r, _t, count = struct.unpack_from("<HHH", g, 0)
    out = []
    for i in range(count):
        w, h, cc, _res, planes, bpp, _size, iid = struct.unpack_from("<BBBBHHIH", g, 6 + i * 14)
        data = pe.get(RT_ICON, iid)
        if data is not None:
            out.append((w, h, cc, planes, bpp, data))
    return out


def group_icons(pe, gid):
    """[(w, h, bpp, Image RGBA)] de um RT_GROUP_ICON, por qualidade decrescente."""
    return _decode([(w, h, bpp, d) for w, h, _cc, _p, bpp, d in _group_entries(pe, gid)])


def ico_file(pe, gid):
    """Um RT_GROUP_ICON num ficheiro .ico (todas as imagens, pela ordem)."""
    entries = _group_entries(pe, gid)
    offset = 6 + 16 * len(entries)
    head, blobs = struct.pack("<HHH", 0, 1, len(entries)), b""
    for w, h, cc, planes, bpp, data in entries:
        head += struct.pack("<BBBBHHII", w, h, cc, 0, planes, bpp, len(data), offset)
        blobs += data
        offset += len(data)
    return head + blobs


def ico_icons(data):
    """[(w, h, bpp, Image RGBA)] de um ficheiro .ico, por qualidade decrescente."""
    _r, _t, count = struct.unpack_from("<HHH", data, 0)
    entries = []
    for i in range(count):
        w, h, _cc, _res, _planes, bpp, size, off = struct.unpack_from("<BBBBHHII", data, 6 + i * 16)
        entries.append((w, h, bpp, data[off:off + size]))
    return _decode(entries)


def _best(icons, size):
    cands = [e for e in icons if e[0] == size]
    return max(cands, key=lambda e: e[2])[3] if cands else None


def best(pe, gid, size):
    """Melhor imagem para um tamanho: a de maior profundidade nesse tamanho."""
    return _best(group_icons(pe, gid), size)


def best_ico(data, size):
    """Como best(), a partir de um ficheiro .ico."""
    return _best(ico_icons(data), size)


def group_ids(pe):
    return sorted((n for t, n in pe.resources if t == RT_GROUP_ICON), key=lambda n: (isinstance(n, str), n))
