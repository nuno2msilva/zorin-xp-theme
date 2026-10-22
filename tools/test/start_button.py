#!/usr/bin/env python3
"""Compara o botão Iniciar desenhado (tools/builders/shelltheme.py) com os
recortes das capturas reais (reference/start-button), píxel a píxel.

    python3 tools/test/start_button.py [pasta para as imagens]

Escreve, para cada estado, quantos píxeis diferem (e quanto) e, com uma
pasta, as imagens desenhadas e um mapa das diferenças ampliado 8×.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402

from builders import shelltheme  # noqa: E402
from lib import assets  # noqa: E402
from lib.paths import ROOT  # noqa: E402

REF = os.path.join(ROOT, "reference", "start-button")


def main(out=None):
    if not os.path.isdir(REF):
        sys.exit(f"Sem os recortes de referência em {REF} (ficam fora do git).")
    work = out or tempfile.mkdtemp()
    os.makedirs(work, exist_ok=True)
    width = shelltheme.start_button(assets.theme("luna"), work)
    print(f"largura: {width} px")
    for state in ("normal", "hover", "active"):
        ours = Image.open(os.path.join(work, f"start-{state}.png")).convert("RGB")
        ref = Image.open(os.path.join(REF, f"iniciar-{state}.png")).convert("RGB")
        if ours.size != ref.size:
            print(f"{state}: tamanho {ours.size} ≠ {ref.size}")
            continue
        a, b = ours.load(), ref.load()
        diffs = {}
        worst = []
        for y in range(ref.height):
            for x in range(ref.width):
                d = max(abs(u - v) for u, v in zip(a[x, y], b[x, y]))
                if d:
                    diffs[x, y] = d
                if d > 8:
                    worst.append((x, y, d))
        big = sum(d > 2 for d in diffs.values())
        print(f"{state}: {len(diffs)} píxeis diferentes, {big} por mais de 2 níveis;"
              f" maiores: {sorted(worst, key=lambda w: -w[2])[:6]}")
        if out:
            m = Image.new("RGB", ref.size)
            for (x, y), d in diffs.items():
                m.putpixel((x, y), (min(255, d * 8), 0, 0) if d > 2 else (0, 60, 0))
            m.resize((ref.width * 8, ref.height * 8), Image.NEAREST).save(
                os.path.join(out, f"diff-{state}.png"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
