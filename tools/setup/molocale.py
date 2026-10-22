#!/usr/bin/env python3
"""Catálogos de tradução com os nomes do XP para o Ficheiros e o ambiente de
trabalho: "Pasta pessoal" -> "O meu computador", "Lixo" -> "Reciclagem",
"Desktop" -> "Ambiente de trabalho".

Copia o catálogo do sistema (o mesmo que a sessão usaria, pela ordem de
LANGUAGE) e muda só essas frases, com a concordância portuguesa ("o lixo" ->
"a Reciclagem", "O lixo está vazio" -> "A Reciclagem está vazia"). O
resultado fica em <saída>/<língua>/LC_MESSAGES/<domínio>.mo; a biblioteca
zorin-xp-gettext.so faz o Ficheiros e o ambiente de trabalho usá-los (os
catálogos do sistema não se mexem).

Uso: molocale.py <pasta de saída>
"""
import os
import re
import struct
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DOMAINS = ("nautilus", "zorin-desktop-icons")
BASES = ("/usr/share/locale-langpack", "/usr/share/locale")
HOME_NAME = "O meu computador"          # shell32.dll 9216
TRASH_NAME = "Reciclagem"               # shell32.dll 8964
DESKTOP_NAME = "Ambiente de trabalho"   # o nome da pasta do XP (o catálogo diz "Desktop")

# (padrão, substituição) pela ordem; os mnemónicos "_" mantêm-se
RULES = [
    (r"\bO _?lixo está vazio\b", "A Reciclagem está vazia"),
    (r"(?<![\w])(_?[Ee]svaziar) (?:o )?(_?)(?:lixo|lixeira)\b", r"\1 a \2Reciclagem"),
    (r"\b([Oo]) lixo tem de ser esvaziado\b", r"a Reciclagem tem de ser esvaziada"),
    (r"\bpara (?:o |a )?(_?)(?:[Ll]ixo|lixeira)\b", r"para a \1Reciclagem"),
    (r"\b(d)(?:o|a) (_?)(?:[Ll]ixo|lixeira)\b", r"\1a \2Reciclagem"),
    (r"\b(n)(?:o|a) (_?)(?:[Ll]ixo|lixeira)\b", r"\1a \2Reciclagem"),
    (r"\bo (_?)[Ll]ixo\b", r"a \1Reciclagem"),
    (r"\bO (_?)[Ll]ixo\b", r"A \1Reciclagem"),
    (r"\ba (_?)lixeira\b", r"a \1Reciclagem"),
    (r"\b(_?)(?:[Ll]ixo|[Ll]ixeira)\b", r"\1Reciclagem"),
    (r"\b(d)a pasta pessoal\b", rf"\1e '{HOME_NAME}'"),
    (r"\b(?:a )?[Pp]asta [Pp]essoal\b", f"'{HOME_NAME}'"),
]
# mensagens que são o próprio nome (rótulos): sem aspas
EXACT = {b"Home": HOME_NAME, b"Trash": TRASH_NAME, b"Desktop": DESKTOP_NAME}


def languages():
    env = os.environ.get("LANGUAGE") or os.environ.get("LANG", "pt_PT").split(".")[0]
    langs = [l for l in env.split(":") if l and l != "en"]
    return langs or ["pt"]


def find_catalog(domain):
    for lang in languages():
        for l in (lang, lang.split("_")[0]):
            for base in BASES:
                p = os.path.join(base, l, "LC_MESSAGES", domain + ".mo")
                if os.path.exists(p):
                    return p
    return None


def read_mo(path):
    data = open(path, "rb").read()
    magic, = struct.unpack_from("<I", data)
    e = "<" if magic == 0x950412de else ">"
    _rev, n, oo, to = struct.unpack_from(e + "4I", data, 4)
    out = []
    for i in range(n):
        ol, of = struct.unpack_from(e + "2I", data, oo + 8 * i)
        tl, tf = struct.unpack_from(e + "2I", data, to + 8 * i)
        out.append((data[of:of + ol], data[tf:tf + tl]))
    return out


def write_mo(path, entries):
    entries = sorted(entries, key=lambda e: e[0])
    n = len(entries)
    oo, to = 28, 28 + 8 * n
    pos = to + 8 * n
    otab, ttab, blob = b"", b"", b""
    for orig, _t in entries:
        otab += struct.pack("<2I", len(orig), pos + len(blob))
        blob += orig + b"\0"
    for _o, trans in entries:
        ttab += struct.pack("<2I", len(trans), pos + len(blob))
        blob += trans + b"\0"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<7I", 0x950412de, 0, n, oo, to, 0, 0) + otab + ttab + blob)


def convert(text):
    for pat, rep in RULES:
        text = re.sub(pat, rep, text)
    return text


def build(out):
    lang = languages()[0]
    made = []
    for domain in DOMAINS:
        src = find_catalog(domain)
        if not src:
            continue
        entries = []
        seen = set()
        for orig, trans in read_mo(src):
            if orig in EXACT:
                trans = EXACT[orig].encode()
            elif orig:          # (o cabeçalho fica)
                trans = b"\0".join(convert(t.decode("utf-8")).encode() for t in trans.split(b"\0"))
            entries.append((orig, trans))
            seen.add(orig)
        # rótulos que o catálogo não traduzia
        for orig, name in EXACT.items():
            if orig not in seen:
                entries.append((orig, name.encode()))
        dst = os.path.join(out, lang, "LC_MESSAGES", domain + ".mo")
        write_mo(dst, entries)
        made.append(domain)
    return made


if __name__ == "__main__":
    print(" ".join(build(sys.argv[1])))
