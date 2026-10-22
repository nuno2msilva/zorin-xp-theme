"""Pastas do projeto, num só sítio.

  windows/<cópia>/   cópias da pasta Windows do XP (fora do git): a origem
                     dos recursos, só lida por tools/extract.py
  assets/            os recursos extraídos, com nomes legíveis: a única
                     entrada da construção (tools/build.py)
  build/             o tema construído (fora do git)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WINDOWS = os.path.join(ROOT, "windows")
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
SRC = os.path.join(ROOT, "src")

# a cópia do Windows de onde se extrai, e a língua dos textos extraídos
DEFAULT_WINDOWS = os.path.join(WINDOWS, "xp-pro-pt")
DEFAULT_LOCALE = "pt-PT"


def find_ci(directory, *names):
    """Caminho dentro de uma cópia do Windows sem olhar a maiúsculas
    (system32/SHELL32.DLL, Fonts/TAHOMA.TTF...): find_ci(raiz, "system32",
    "shell32.dll"). Erro se não existir."""
    path = directory
    for name in names:
        low = name.lower()
        match = next((e for e in os.listdir(path) if e.lower() == low), None)
        if match is None:
            raise FileNotFoundError(os.path.join(path, name))
        path = os.path.join(path, match)
    return path
