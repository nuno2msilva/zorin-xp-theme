#!/usr/bin/env python3
"""Compara duas construções (build/) ficheiro a ficheiro: os .xpi pelo
conteúdo (o zip guarda datas), as imagens pelos píxeis quando os bytes
diferem. Uso: compare_builds.py <antes> <depois>"""
import io, json, os, sys, zipfile
from PIL import Image

def files(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = p
    return out

def same_image(a, b):
    try:
        ia, ib = Image.open(io.BytesIO(a)), Image.open(io.BytesIO(b))
        return ia.size == ib.size and ia.convert("RGBA").tobytes() == ib.convert("RGBA").tobytes()
    except Exception:
        return False

def same(name, a, b):
    if a == b:
        return True
    if name.endswith(".xpi"):
        za, zb = zipfile.ZipFile(io.BytesIO(a)), zipfile.ZipFile(io.BytesIO(b))
        na, nb = sorted(za.namelist()), sorted(zb.namelist())
        return na == nb and all(same(n, za.read(n), zb.read(n)) for n in na)
    if name.lower().endswith((".png", ".bmp", ".gif", ".jpg")):
        return same_image(a, b)
    if name.lower().endswith(".json"):
        import json
        try:
            return json.loads(a) == json.loads(b)
        except ValueError:
            return False
    return False

A, B = files(sys.argv[1]), files(sys.argv[2])
only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
diff = [n for n in sorted(set(A) & set(B)) if not same(n, open(A[n], "rb").read(), open(B[n], "rb").read())]
for label, items in (("só no primeiro", only_a), ("só no segundo", only_b), ("diferentes", diff)):
    print(f"{label}: {len(items)}")
    for n in items[:30]:
        print("   ", n)
sys.exit(1 if only_a or only_b or diff else 0)
