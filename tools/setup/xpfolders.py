#!/usr/bin/env python3
"""Home folders with the names of Portuguese XP (shell32.dll texts).

    Documentos -> Os meus documentos      Imagens -> As minhas imagens
    Música -> A minha música              Vídeos -> Os meus vídeos
    Secretária -> Ambiente de trabalho    Transferências -> Downloads
    Público -> Documentos partilhados     Modelos (the same)

The folders are renamed and the old name stays as a shortcut (symbolic link)
hidden in Files (~/.hidden): paths stored in programs, shortcuts and links
pointing to ~/Documentos/... keep working. Undo does not need these
shortcuts: one that nothing uses can be deleted.
"As minhas imagens", "A minha música", "Os meus vídeos" and "Downloads" move
inside "Os meus documentos", as in XP (also when the folders already had
the XP names): on the same disk it is only a rename, nothing is copied; the
previous places (~/Imagens, ~/As minhas imagens...) stay as hidden
shortcuts. A folder on another disk, or in use, is not moved: a shortcut to
it goes inside "Os meus documentos", with the folder's icon. Updates
~/.config/user-dirs.dirs and the sidebar bookmarks.

Everything that changes is recorded in ~/.local/share/zorin-xp/folders.json
for undo.

Usage: xpfolders.py apply | undo     (ZXP_HOME=<folder> to rehearse elsewhere)
"""
import json
import os
import shutil
import sys
from urllib.parse import quote, unquote

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOME = os.environ.get("ZXP_HOME") or os.path.expanduser("~")
CONFIG = os.path.join(HOME, ".config")
STATE = os.path.join(HOME, ".local", "share", "zorin-xp", "folders.json")
USER_DIRS = os.path.join(CONFIG, "user-dirs.dirs")
BOOKMARKS = os.path.join(CONFIG, "gtk-3.0", "bookmarks")
HIDDEN = os.path.join(HOME, ".hidden")

XP_NAMES = {                       # shell32.dll: 9100, 9076, 9105, 9107, 9092, 21785, 9078
    "XDG_DOCUMENTS_DIR": "Os meus documentos",
    "XDG_PICTURES_DIR": "As minhas imagens",
    "XDG_MUSIC_DIR": "A minha música",
    "XDG_VIDEOS_DIR": "Os meus vídeos",
    "XDG_DESKTOP_DIR": "Ambiente de trabalho",
    "XDG_DOWNLOAD_DIR": "Downloads",          # the user's request (XP did not have it)
    "XDG_PUBLICSHARE_DIR": "Documentos partilhados",
    "XDG_TEMPLATES_DIR": "Modelos",
}
# inside "Os meus documentos" (into_documents), or shortcuts in there with
# the folder's icon when they cannot be moved (the Files extension hides the
# shortcut arrow)
INSIDE_DOCUMENTS = {"XDG_PICTURES_DIR": "folder-pictures", "XDG_MUSIC_DIR": "folder-music",
                    "XDG_VIDEOS_DIR": "folder-videos", "XDG_DOWNLOAD_DIR": "folder-download"}


# GNOME metadata (gvfs: the shortcuts' "Allow Launching", the position of
# the desktop icons, the folders' view and icon...) is stored by path: when
# a folder is renamed it moves to the new path. Only the first levels
# (that is where it is; walking everything would be slow).
META_DEPTH = 3
SKIP = {".git", "node_modules", "__pycache__", ".cache"}


def collect_meta(root, depth=META_DEPTH):
    from gi.repository import Gio
    out = {}

    def attrs(info):
        d = {}
        for k in info.list_attributes("metadata") or []:
            t = info.get_attribute_type(k)
            if t == Gio.FileAttributeType.STRINGV:
                d[k] = ("v", info.get_attribute_stringv(k))
            else:
                d[k] = ("s", info.get_attribute_as_string(k))
        return d

    def walk(path, rel, level):
        f = Gio.File.new_for_path(path)
        try:
            info = f.query_info("metadata::*", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
            d = attrs(info)
            if d:
                out[rel] = d
            if level >= depth or not os.path.isdir(path) or os.path.islink(path):
                return
            for child in f.enumerate_children("standard::name,standard::type,metadata::*",
                                              Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None):
                name = child.get_name()
                if name in SKIP:
                    continue
                crel = os.path.join(rel, name) if rel else name
                if child.get_file_type() == Gio.FileType.DIRECTORY:
                    walk(os.path.join(path, name), crel, level + 1)
                else:
                    d = attrs(child)
                    if d:
                        out[crel] = d
        except Exception as e:   # (files without permission, etc.)
            print(f"  metadados não lidos: {path}: {e}")
    walk(root, "", 0)
    return out


def apply_meta(root, meta, only_missing=True):
    from gi.repository import Gio
    n = 0
    for rel, d in meta.items():
        f = Gio.File.new_for_path(os.path.join(root, rel) if rel else root)
        try:
            have = f.query_info("metadata::*", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
        except Exception:
            continue
        info = Gio.FileInfo()
        for k, (t, v) in d.items():
            if only_missing and have.has_attribute(k):
                continue
            if t == "v":
                info.set_attribute_stringv(k, v)
            else:
                info.set_attribute_string(k, v)
            n += 1
        if info.list_attributes("metadata"):
            try:
                f.set_attributes_from_info(info, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
            except Exception as e:
                print(f"  metadados não escritos: {rel}: {e}")
    return n


def read_user_dirs():
    out = {}
    if os.path.exists(USER_DIRS):
        for line in open(USER_DIRS, encoding="utf-8"):
            line = line.strip()
            if line.startswith("XDG_") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip('"').replace("$HOME", HOME)
    return out


def write_user_dirs(dirs):
    with open(USER_DIRS, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for line in lines:
        k = line.split("=", 1)[0].strip()
        if k in dirs:
            rel = os.path.relpath(dirs[k], HOME)
            line = f'{k}="$HOME/{rel}"'
        out.append(line)
    with open(USER_DIRS, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def uri(path):
    return "file://" + quote(path)


def rewrite_bookmarks(mapping):
    """mapping: old path -> new (also for whatever is inside)."""
    if not os.path.exists(BOOKMARKS):
        return
    out = []
    for line in open(BOOKMARKS, encoding="utf-8").read().splitlines():
        target, sep, label = line.partition(" ")
        if target.startswith("file://"):
            path = unquote(target[7:])
            # (the longest path first: Os meus documentos/A minha música before
            # Os meus documentos)
            for old, new in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
                if path == old or path.startswith(old + "/"):
                    path = new + path[len(old):]
                    target = uri(path)
                    break
        out.append(target + (sep + label if sep else ""))
    with open(BOOKMARKS, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def hidden_lines():
    return open(HIDDEN, encoding="utf-8").read().splitlines() if os.path.exists(HIDDEN) else []


def holders(path):
    """Programs with files open (or working) inside path."""
    out = set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            links = [os.readlink(f"/proc/{pid}/cwd")]
            links += [os.readlink(f"/proc/{pid}/fd/{fd}") for fd in os.listdir(f"/proc/{pid}/fd")]
        except OSError:
            continue
        if any(t == path or t.startswith(path + "/") for t in links):
            try:
                out.add(open(f"/proc/{pid}/comm").read().strip())
            except OSError:
                pass
    return sorted(out)


def relink(link, target):
    """link (symbolic link) now points to target (relative path)."""
    if os.path.islink(link):
        os.remove(link)
    os.symlink(os.path.relpath(target, os.path.dirname(link)), link)


def into_documents(state):
    """As minhas imagens, A minha música, Os meus vídeos and Downloads into
    "Os meus documentos" (the ones that are not there yet)."""
    from gi.repository import Gio
    dirs = read_user_dirs()
    docs = dirs.get("XDG_DOCUMENTS_DIR")
    if not docs or not os.path.isdir(docs) or os.path.realpath(docs) == os.path.realpath(HOME):
        return
    hidden = hidden_lines()
    moved = {}
    for key in INSIDE_DOCUMENTS:
        cur = dirs.get(key)
        if not cur or os.path.islink(cur) or not os.path.isdir(cur):
            continue
        if os.path.realpath(cur) in (os.path.realpath(HOME), os.path.realpath(docs)) or \
                os.path.dirname(os.path.realpath(cur)) == os.path.realpath(docs):
            continue
        name = os.path.basename(cur)
        new = os.path.join(docs, name)
        ours = os.path.islink(new) and new in state["inside"]
        if os.path.lexists(new) and not ours:
            print(f"  não mudada: já existe '{new}'")
            continue
        if os.stat(cur).st_dev != os.stat(docs).st_dev:
            print(f"  não mudada (está noutro disco): {cur}")
            continue
        busy = holders(cur)
        if busy:
            print(f"  não mudada (em uso por {', '.join(busy)}): {cur}")
            continue
        if ours:
            # the previous shortcut goes (Gio: its metadata too)
            Gio.File.new_for_path(new).delete(None)
            state["inside"].remove(new)
        # Gio.File.move takes the GNOME metadata of the whole folder along
        Gio.File.new_for_path(cur).move(Gio.File.new_for_path(new),
                                        Gio.FileCopyFlags.NOFOLLOW_SYMLINKS, None, None)
        relink(cur, new)
        state.setdefault("moved", []).append([cur, new])
        # the shortcuts of the previous names (~/Imagens) go straight to the new place
        for r in state["renames"]:
            if r[1] == cur:
                r[1] = new
                if r[0] and os.path.islink(r[0]):
                    relink(r[0], new)
        if os.path.dirname(cur) == HOME and name not in hidden:
            hidden.append(name)
            state["hidden"].append(name)
        moved[key] = new
        print(f"  {name} -> {os.path.basename(docs)}/{name}")
    if moved:
        write_user_dirs(moved)
        rewrite_bookmarks({dirs[k]: v for k, v in moved.items()})
        with open(HIDDEN, "w", encoding="utf-8") as f:
            f.write("\n".join(hidden) + "\n")


def inside_documents(state):
    """For the folders that could not go inside "Os meus documentos": a
    shortcut in there (if missing) with the folder's icon."""
    from gi.repository import Gio
    dirs = read_user_dirs()
    docs = dirs.get("XDG_DOCUMENTS_DIR")
    if not docs or not os.path.isdir(docs):
        return
    for key, icon in INSIDE_DOCUMENTS.items():
        target = dirs.get(key)
        if not target or not os.path.isdir(target) or os.path.realpath(target) == os.path.realpath(docs):
            continue
        if os.path.dirname(os.path.realpath(target)) == os.path.realpath(docs):
            continue
        link = os.path.join(docs, os.path.basename(target))
        if not os.path.lexists(link):
            os.symlink(os.path.relpath(target, docs), link)
            state["inside"].append(link)
        if link in state["inside"]:
            try:
                Gio.File.new_for_path(link).set_attribute_string(
                    "metadata::custom-icon-name", icon, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
            except Exception as e:
                print(f"  (ícone de {link}: {e})")


def apply():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
        into_documents(state)
        inside_documents(state)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("As pastas já têm os nomes do XP (\"Os meus documentos\" acertado).")
        return
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = {"renames": [], "inside": [], "hidden": []}
    for name, path in ((USER_DIRS, "user-dirs.dirs"), (BOOKMARKS, "bookmarks")):
        if os.path.exists(name):
            shutil.copy2(name, os.path.join(os.path.dirname(STATE), f"folders-{path}.orig"))
    dirs = read_user_dirs()
    new_dirs = {}
    mapping = {}
    for key, xp in XP_NAMES.items():
        old = dirs.get(key)
        new = os.path.join(HOME, xp)
        if not old or os.path.normpath(old) == os.path.normpath(HOME):
            continue
        if os.path.normpath(old) == new:
            continue
        if os.path.lexists(new):
            print(f"  ignorado: já existe '{new}'")
            continue
        if os.path.isdir(old) and not os.path.islink(old):
            meta = collect_meta(old)
            os.rename(old, new)
            apply_meta(new, meta)
            # the old name stays as a hidden shortcut: nothing breaks
            os.symlink(os.path.basename(new), old)
            state["renames"].append([old, new])
            mapping[old] = new
            print(f"  {os.path.basename(old)} -> {xp}")
        else:
            os.makedirs(new, exist_ok=True)
            state["renames"].append([None, new])
        new_dirs[key] = new
    write_user_dirs(new_dirs)
    rewrite_bookmarks(mapping)

    hidden = hidden_lines()
    for old, _new in state["renames"]:
        if old and os.path.basename(old) not in hidden:
            hidden.append(os.path.basename(old))
            state["hidden"].append(os.path.basename(old))
    if state["hidden"]:
        with open(HIDDEN, "w", encoding="utf-8") as f:
            f.write("\n".join(hidden) + "\n")

    into_documents(state)
    inside_documents(state)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print("Pastas com os nomes do XP.")


def undo():
    if not os.path.exists(STATE):
        return
    state = json.load(open(STATE, encoding="utf-8"))
    from gi.repository import Gio
    for link in state["inside"]:
        if os.path.islink(link):
            Gio.File.new_for_path(link).delete(None)

    def points(link, target):
        return os.path.islink(link) and \
            os.readlink(link) == os.path.relpath(target, os.path.dirname(link))
    # the shortcuts of the places the folders went through (~/A minha música)
    for cur, new in state.get("moved", []):
        if points(cur, new):
            os.remove(cur)
    for old, new in reversed(state["renames"]):
        if not old:
            continue
        # only if the old name is still our shortcut, or free (the shortcut
        # may have been deleted): never over anything else
        free = not os.path.lexists(old)
        if (free or points(old, new)) and os.path.isdir(new):
            if not free:
                os.remove(old)
            Gio.File.new_for_path(new).move(Gio.File.new_for_path(old),
                                            Gio.FileCopyFlags.NOFOLLOW_SYMLINKS, None, None)
            print(f"  {os.path.basename(new)} -> {os.path.basename(old)}")
        else:
            print(f"  deixado como está: {new}")
    if state["hidden"]:
        keep = [h for h in hidden_lines() if h not in state["hidden"]]
        if keep:
            with open(HIDDEN, "w", encoding="utf-8") as f:
                f.write("\n".join(keep) + "\n")
        elif os.path.exists(HIDDEN):
            os.remove(HIDDEN)
    base = os.path.dirname(STATE)
    orig = os.path.join(base, "folders-user-dirs.dirs.orig")
    if os.path.exists(orig):
        shutil.move(orig, USER_DIRS)
    # bookmarks: only the paths go back (the ones added in the meantime stay)
    rewrite_bookmarks({new: old for old, new in state["renames"] if old})
    orig = os.path.join(base, "folders-bookmarks.orig")
    if os.path.exists(orig):
        os.remove(orig)
    os.remove(STATE)
    print("Pastas repostas.")


def remeta():
    """For folders that were renamed without taking their metadata (the first
    version): the old name comes back for a moment, the metadata left with
    it is read and moved to the new name (without deleting what is there)."""
    if not os.path.exists(STATE):
        return
    state = json.load(open(STATE, encoding="utf-8"))
    for old, new in state["renames"]:
        if not old or not (os.path.islink(old) and os.path.isdir(new)):
            continue
        os.remove(old)
        os.rename(new, old)
        try:
            meta = collect_meta(old)
        finally:
            os.rename(old, new)
            os.symlink(os.path.basename(new), old)
        n = apply_meta(new, meta)
        print(f"  {os.path.basename(new)}: {n} metadados recuperados")


if __name__ == "__main__":
    {"apply": apply, "undo": undo, "remeta": remeta}[sys.argv[1]]()
