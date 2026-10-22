"""Leitura mínima de ficheiros TrueType (as tabelas, sem dependências).

  t = tables("tahoma.ttf")         {"head": bytes, "OS/2": bytes, ...}
  gdi_ascent_descent(t, 19)        (tmAscent, tmDescent) do GDI nesse tamanho
"""
import struct


def tables(path):
    """{etiqueta: bytes} de todas as tabelas do ficheiro."""
    with open(path, "rb") as f:
        data = f.read()
    n, = struct.unpack_from(">H", data, 4)
    out = {}
    for i in range(n):
        tag, _sum, off, ln = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        out[tag.decode("latin-1")] = data[off:off + ln]
    return out


def gdi_ascent_descent(t, px):
    """A subida e a descida que o GDI dá à letra (tmAscent/tmDescent): as
    métricas Windows da tabela OS/2 (usWinAscent/usWinDescent) à escala."""
    upem, = struct.unpack_from(">H", t["head"], 18)
    win_asc, win_desc = struct.unpack_from(">HH", t["OS/2"], 74)
    return round(win_asc * px / upem), round(win_desc * px / upem)
