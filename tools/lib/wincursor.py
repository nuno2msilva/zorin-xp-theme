"""Descodificação de cursores do Windows (recursos RT_CURSOR, .cur e .ani)."""
import struct

from PIL import Image

RT_CURSOR = 1
RT_GROUP_CURSOR = 12


def _palette(dib, hsize, bpp, ncolors):
    n = ncolors or (1 << bpp)
    pal = []
    for i in range(n):
        b, g, r, _ = struct.unpack_from("<BBBB", dib, hsize + i * 4)
        pal.append((r, g, b))
    return pal, hsize + n * 4


def decode_dib_cursor(dib):
    """DIB de ícone/cursor (altura dobrada: XOR + máscara AND) -> RGBA.

    Píxeis com AND=1 e XOR!=0 são de "inversão" (ex.: cursor de texto);
    não há equivalente em Xcursor, por isso ficam pretos opacos, que é como
    aparecem sobre fundos claros.
    """
    if dib[:8] == b"\x89PNG\r\n\x1a\n":
        import io
        return Image.open(io.BytesIO(dib)).convert("RGBA")
    hsize, w, h2, _planes, bpp, comp, _isz, _xr, _yr, ncol = struct.unpack_from("<IiiHHIIiiI", dib, 0)
    h = abs(h2) // 2
    img = Image.new("RGBA", (w, h))
    px = img.load()
    if bpp <= 8:
        pal, off = _palette(dib, hsize, bpp, ncol)
    else:
        pal, off = None, hsize
    xor_stride = ((w * bpp + 31) // 32) * 4
    and_off = off + xor_stride * h
    and_stride = ((w + 31) // 32) * 4
    has_alpha = False
    inverted = []
    if bpp == 32:
        has_alpha = any(dib[off + i * 4 + 3] for i in range(w * h))
    for y in range(h):
        row = off + (h - 1 - y) * xor_stride
        arow = and_off + (h - 1 - y) * and_stride
        for x in range(w):
            if bpp == 32:
                b, g, r, a = dib[row + x * 4:row + x * 4 + 4]
                rgb = (r, g, b)
            elif bpp == 24:
                b, g, r = dib[row + x * 3:row + x * 3 + 3]
                rgb, a = (r, g, b), 255
            else:
                bit = x * bpp
                byte = dib[row + bit // 8]
                idx = (byte >> (8 - bpp - bit % 8)) & ((1 << bpp) - 1)
                rgb, a = pal[idx], 255
            mask = (dib[arow + x // 8] >> (7 - x % 8)) & 1 if and_off + and_stride * h <= len(dib) else 0
            if has_alpha:
                px[x, y] = (*rgb, a)
            elif mask:
                # transparente (XOR preto) ou inversão (XOR não preto)
                if rgb == (0, 0, 0):
                    px[x, y] = (0, 0, 0, 0)
                else:
                    px[x, y] = (0, 0, 0, 255)
                    inverted.append((x, y))
            else:
                px[x, y] = (*rgb, 255)
    img.inverted = inverted       # píxeis de inversão (para cursors.invert_halo)
    return img


def decode_cursor_resource(data):
    """Recurso RT_CURSOR: WORD hotx, WORD hoty, DIB."""
    hx, hy = struct.unpack_from("<HH", data, 0)
    return decode_dib_cursor(data[4:]), (hx, hy)


def group_cursor(pe, group_id):
    """Devolve [(img, hotspot)] para todos os tamanhos de um RT_GROUP_CURSOR."""
    g = pe.get(RT_GROUP_CURSOR, group_id)
    _r, _t, count = struct.unpack_from("<HHH", g, 0)
    out = []
    for i in range(count):
        w, h2, _planes, _bpp, _size, cid = struct.unpack_from("<HHHHIH", g, 6 + i * 14)
        out.append(decode_cursor_resource(pe.get(RT_CURSOR, cid)))
    return out


def read_cur(data, offset=0):
    """Ficheiro .cur -> [(img, hotspot)]."""
    _r, typ, count = struct.unpack_from("<HHH", data, offset)
    out = []
    for i in range(count):
        e = offset + 6 + i * 16
        _w, _h, _c, _r2, hx, hy, size, off = struct.unpack_from("<BBBBHHII", data, e)
        img = decode_dib_cursor(data[offset + off:offset + off + size])
        out.append((img, (hx, hy) if typ == 2 else (0, 0)))
    return out


def read_ani(data):
    """Ficheiro .ani (RIFF ACON) -> (frames [(img, hotspot)], delays_ms por passo)."""
    assert data[:4] == b"RIFF" and data[8:12] == b"ACON", "não é .ani"
    pos = 12
    frames, rate, seq = [], None, None
    nsteps, jif = 0, 10
    while pos < len(data) - 8:
        cid, size = struct.unpack_from("<4sI", data, pos)
        body = pos + 8
        if cid == b"anih":
            _cb, nframes, nsteps, _cx, _cy, _bc, _np, jif, _fl = struct.unpack_from("<9I", data, body)
        elif cid == b"rate":
            rate = list(struct.unpack_from(f"<{size // 4}I", data, body))
        elif cid == b"seq ":
            seq = list(struct.unpack_from(f"<{size // 4}I", data, body))
        elif cid == b"LIST" and data[body:body + 4] == b"fram":
            p = body + 4
            while p < body + size:
                fid, fsize = struct.unpack_from("<4sI", data, p)
                if fid == b"icon":
                    frames.append(read_cur(data, p + 8)[0])
                p += 8 + fsize + (fsize & 1)
            size = size  # noqa
        pos = body + size + (size & 1)
    steps = seq if seq else list(range(len(frames)))
    delays = [(rate[i] if rate else jif) * 1000 // 60 for i in range(len(steps))]
    return [frames[s] for s in steps], delays
