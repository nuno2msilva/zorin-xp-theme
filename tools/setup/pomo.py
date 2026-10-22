#!/usr/bin/env python3
"""Compila um ficheiro .po simples (msgid/msgstr, sem plurais) para .mo.

Uso: pomo.py <entrada.po> <saida.mo>  (o msgfmt nem sempre está instalado)
"""
import ast
import struct
import sys
import os

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse(path):
    entries, key, cur = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("msgid "):
            key, cur = "id", [ast.literal_eval(line[6:])]
            mid = cur
        elif line.startswith("msgstr "):
            key, cur = "str", [ast.literal_eval(line[7:])]
            entries["".join(mid)] = cur
        elif line.startswith('"') and cur is not None:
            cur.append(ast.literal_eval(line))
    return {k: "".join(v) for k, v in entries.items() if "".join(v) or not k}


def write_mo(entries, path):
    keys = sorted(entries)
    ids = [k.encode() for k in keys]
    strs = [entries[k].encode() for k in keys]
    n = len(keys)
    o_ids, o_strs = 28, 28 + n * 8
    data_off = 28 + n * 16
    id_tab, str_tab, blob = [], [], b""
    for s in ids:
        id_tab.append((len(s), data_off + len(blob)))
        blob += s + b"\0"
    for s in strs:
        str_tab.append((len(s), data_off + len(blob)))
        blob += s + b"\0"
    with open(path, "wb") as f:
        f.write(struct.pack("<7I", 0x950412DE, 0, n, o_ids, o_strs, 0, 0))
        for t in id_tab + str_tab:
            f.write(struct.pack("<2I", *t))
        f.write(blob)


if __name__ == "__main__":
    write_mo(parse(sys.argv[1]), sys.argv[2])
