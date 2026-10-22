"""Larguras dos caracteres como no Windows XP.

O GDI do XP posiciona o texto com as larguras por tamanho gravadas na própria
fonte (tabela hdmx, as do hinting) e sem kerning. O Pango/HarfBuzz usa a
largura teórica (hmtx) arredondada ao píxel e aplica o kerning: em Tahoma Bold
a 11 px, por exemplo, o "m" fica com 10 px em vez dos 11 do XP e o texto sai
mais apertado.

A hmtx não se pode mudar: o hinting das fontes da Microsoft usa-a para
desenhar as letras (com outra largura o "s" negrito passa de 5 para 4 px).
Em vez disso acrescenta-se uma tabela GPOS com um ajuste de avanço por glifo
(feature "dist", ligada por omissão no HarfBuzz) para que, no tamanho
principal da interface, a largura seja exatamente a do XP; o FreeType ignora a
GPOS e desenha as letras como antes. Retira-se também a tabela kern. Só se
alteram as cópias instaladas na pasta pessoal.
"""
import struct

# Tamanho principal (px) de cada família na interface do XP a 96 ppp
PRIMARY_PPEM = {"tahoma": 11, "verdana": 11, "micross": 11, "trebuc": 13, "framd": 19}
DROP = {"kern", "DSIG"}


def _tables(data):
    n = struct.unpack(">H", data[4:6])[0]
    out = {}
    for i in range(n):
        tag, _cs, off, ln = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
        out[tag.decode("latin1")] = data[off:off + ln]
    return data[:4], out


def _checksum(b):
    b = b + b"\0" * (-len(b) % 4)
    return sum(struct.unpack(f">{len(b) // 4}I", b)) & 0xFFFFFFFF


def _write(sfnt, tables):
    tags = sorted(tables)
    n = len(tags)
    es = max(k for k in range(16) if 2 ** k <= n)
    sr = 16 * 2 ** es
    head = bytearray(tables["head"])
    head[8:12] = b"\0\0\0\0"          # checkSumAdjustment calculado no fim
    tables = dict(tables, head=bytes(head))
    out = bytearray(sfnt + struct.pack(">HHHH", n, sr, es, 16 * n - sr))
    off = 12 + 16 * n
    body = bytearray()
    for tag in tags:
        t = tables[tag]
        out += struct.pack(">4sIII", tag.encode("latin1"), _checksum(t), off + len(body), len(t))
        body += t + b"\0" * (-len(t) % 4)
    font = bytearray(out + body)
    adj = (0xB1B0AFBA - _checksum(bytes(font))) & 0xFFFFFFFF
    ho = off + sum(len(tables[t]) + (-len(tables[t]) % 4) for t in tags[:tags.index("head")])
    font[ho + 8:ho + 12] = struct.pack(">I", adj)
    return bytes(font)


def _hdmx(t, num_glyphs):
    if "hdmx" not in t:
        return {}
    h = t["hdmx"]
    _ver, nrec, size = struct.unpack(">HhI", h[:8])
    recs = {}
    for r in range(nrec):
        o = 8 + r * size
        recs[h[o]] = h[o + 2:o + 2 + num_glyphs]
    return recs


def _gpos_single_adv(deltas):
    """GPOS com um lookup SinglePos (avanço X) na feature dist, para DFLT e latn."""
    glyphs = sorted(deltas)
    n = len(glyphs)
    # SinglePosFormat2 + Coverage formato 1
    cov = struct.pack(">HH", 1, n) + struct.pack(f">{n}H", *glyphs)
    sub_head = 8 + 2 * n
    sub = struct.pack(">HHHH", 2, sub_head, 0x0004, n) + struct.pack(f">{n}h", *(deltas[g] for g in glyphs)) + cov
    lookup = struct.pack(">HHHH", 1, 0, 1, 8) + sub
    lookup_list = struct.pack(">HH", 1, 4) + lookup
    feature = struct.pack(">HHH", 0, 1, 0)
    feature_list = struct.pack(">H4sH", 1, b"dist", 8) + feature
    langsys = struct.pack(">HHHH", 0, 0xFFFF, 1, 0)
    script = struct.pack(">HH", 4, 0) + langsys
    script_list = struct.pack(">H", 2) + struct.pack(">4sH", b"DFLT", 14) + struct.pack(">4sH", b"latn", 14 + len(script)) + script + script
    so = 10
    fo = so + len(script_list)
    lo = fo + len(feature_list)
    return struct.pack(">HHHHH", 1, 0, so, fo, lo) + script_list + feature_list + lookup_list


def fix(src, dst, family):
    """Copia src para dst com as larguras do XP. Devolve nº de glifos ajustados."""
    sfnt, t = _tables(open(src, "rb").read())
    upem = struct.unpack(">H", t["head"][18:20])[0]
    num_glyphs = struct.unpack(">H", t["maxp"][4:6])[0]
    n_hm = struct.unpack(">H", t["hhea"][34:36])[0]
    hdmx = _hdmx(t, num_glyphs)
    primary = PRIMARY_PPEM.get(family)
    deltas = {}
    if primary in hdmx and "GPOS" not in t:
        hm = t["hmtx"]
        for g in range(num_glyphs):
            k = min(g, n_hm - 1)
            adv = struct.unpack(">H", hm[4 * k:4 * k + 2])[0]
            w = hdmx[primary][g]
            if not w:
                continue
            # largura exata do XP no tamanho principal (o Pango pode acumular
            # posições fracionárias, por isso não basta arredondar para lá)
            d = int(round(w * upem / primary)) - adv
            if d:
                deltas[g] = d
        if deltas:
            t["GPOS"] = _gpos_single_adv(deltas)
    for tag in DROP:
        t.pop(tag, None)
    with open(dst, "wb") as f:
        f.write(_write(sfnt, t))
    return len(deltas)


def family_of(filename):
    low = filename.lower()
    return next((k for k in PRIMARY_PPEM if low.startswith(k)), None)
