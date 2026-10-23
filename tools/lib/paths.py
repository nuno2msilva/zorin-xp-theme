"""The project's folders, in one place.

  windows/<copy>/    copies of the XP Windows folder (outside git): the
                     source of the resources, only read by tools/extract.py
  assets/            the extracted resources, with readable names: the only
                     input of the build (tools/build.py)
  build/             the built theme (outside git)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WINDOWS = os.path.join(ROOT, "windows")
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
SRC = os.path.join(ROOT, "src")

# the Windows copy to extract from, and the language of the extracted texts
DEFAULT_WINDOWS = os.path.join(WINDOWS, "xp-pro-pt")
DEFAULT_LOCALE = "pt-PT"


def find_ci(directory, *names):
    """Path inside a Windows copy, case-insensitively
    (system32/SHELL32.DLL, Fonts/TAHOMA.TTF...): find_ci(root, "system32",
    "shell32.dll"). Error if it does not exist."""
    path = directory
    for name in names:
        low = name.lower()
        match = next((e for e in os.listdir(path) if e.lower() == low), None)
        if match is None:
            raise FileNotFoundError(os.path.join(path, name))
        path = os.path.join(path, match)
    return path
