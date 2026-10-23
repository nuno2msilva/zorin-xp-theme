#!/usr/bin/env python3
"""Zen preferences for the Internet Explorer look (src/zen-ie).

  apply <profile>  IE buttons on the navigation bar (Home, Search,
                   Favorites, History), userChrome.css enabled, system
                   frame (the XP title bar), menu bar always visible, the
                   Find window allowed in private windows and Zen's Ctrl+F
                   turned off (the Find window's stays). Saves the old
                   values in <profile>/zorin-xp-ie.json.
  undo <profile>   restores the saved values.

Zen must be closed (it writes prefs.js when it exits).
"""
import json
import os
import re
import sys

# (also runs on its own: tools/ on the path, for "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Favorites and History: the buttons of the Explorer bars' extensions
FAVORITES = "zorin-xp-ie-favorites_zorin-xp_local-browser-action"
HISTORY = "zorin-xp-ie-history_zorin-xp_local-browser-action"
FIND = "zorin-xp-ie-find_zorin-xp_local-browser-action"       # Search: the Find window
NAV = ["back-button", "forward-button", "stop-reload-button", "home-button",
       FIND, FAVORITES, HISTORY]
REPLACED = ["bookmarks-menu-button", "history-panelmenu", "find-button"]   # (the previous ones: removed)
PREFS = {
    "toolkit.legacyUserProfileCustomizations.stylesheets": True,
    "browser.tabs.inTitlebar": 0,
    "zen.view.use-single-toolbar": False,
    # full address in the box, like IE ("https://" included)
    "browser.urlbar.trimURLs": False,
    "browser.urlbar.trimHttps": False,
    # compact mode: hides only the sidebar (the IE bars stay)
    "zen.view.compact.hide-toolbar": False,
    "zen.view.compact.hide-tabbar": True,
    # on start, go back to the last page seen (Zen picked an empty tab)
    "zen.workspaces.continue-where-left-off": True,
    # switching spaces swaps the tabs and the name at once, without sliding
    "zen.workspaces.switch-animation-duration": 0,
    # without the "New tab opened in the background!" notice (IE did not have it)
    "zen.view.compact.show-background-tab-toast": False,
    # on start, the address box stays closed (Zen opened it with the
    # suggestion list when the initial tab is empty)
    "zen.urlbar.open-on-startup": False,
    # the IE sounds extension (local, without Mozilla's signature), put in the
    # profile's extensions folder: enabled without asking
    "xpinstall.signatures.required": False,
    "extensions.autoDisableScopes": 14,
    # (the per-site folder one uses an experimental API: Zen allows it by default)
    "extensions.experiments.enabled": True,
    # page scrollbars like XP's: always visible, 17 px, with the arrows at the
    # top and bottom (Luna's images come from the src/zen-ie/scrollbars
    # extension; userContent.css only gives the fallback colours)
    "widget.gtk.overlay-scrollbars.enabled": False,
    "widget.non-native-theme.scrollbar.style": 4,
    "ui.scrollArrowStyle": 4097,
    # (the thin ones some sites ask for stay normal, as in XP)
    "layout.css.scrollbar-width-thin.disabled": True,
}
# the Find window is kept ready in a private window (see src/zen-ie/find)
PRIVATE = ["zorin-xp-ie-find@zorin-xp.local"]
PB = "internal:privateBrowsingAllowed"
# Zen shortcuts turned off: Ctrl+F becomes the Find window's
SHORTCUTS_OFF = ["key_find"]
STATE = "zorin-xp-ie.json"
LINE = re.compile(r'^user_pref\("([^"]+)",\s*(.*)\);\s*$')


def read(profile):
    out = {}
    for line in open(os.path.join(profile, "prefs.js"), encoding="utf-8"):
        m = LINE.match(line)
        if m:
            out[m.group(1)] = json.loads(m.group(2))
    return out


def write(profile, changes):
    """changes: nome -> valor (None = apagar)."""
    p = os.path.join(profile, "prefs.js")
    lines = open(p, encoding="utf-8").read().splitlines()
    out, done = [], set()
    for line in lines:
        m = LINE.match(line)
        if m and m.group(1) in changes:
            done.add(m.group(1))
            v = changes[m.group(1)]
            if v is not None:
                out.append(f'user_pref("{m.group(1)}", {json.dumps(v)});')
            continue
        out.append(line)
    for k, v in changes.items():
        if k not in done and v is not None:
            out.append(f'user_pref("{k}", {json.dumps(v)});')
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def placements(state):
    d = json.loads(state) if state else {"placements": {}, "currentVersion": 26}
    nav = d["placements"].get("nav-bar", [])
    rest = [w for w in nav if w not in NAV and w not in REPLACED]
    d["placements"]["nav-bar"] = NAV + rest
    for area, widgets in d["placements"].items():
        if area != "nav-bar":
            d["placements"][area] = [w for w in widgets if w not in NAV]
    return json.dumps(d, separators=(",", ":"))


def xulstore(profile, autohide):
    p = os.path.join(profile, "xulstore.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    doc = d.setdefault("chrome://browser/content/browser.xhtml", {})
    old = doc.get("toolbar-menubar", {}).get("autohide")
    if autohide is None:
        doc.get("toolbar-menubar", {}).pop("autohide", None)
    else:
        doc.setdefault("toolbar-menubar", {})["autohide"] = autohide
    json.dump(d, open(p, "w"))
    return old


def private_windows(profile, ids, allow):
    """Grants (or removes) the permission to run in private windows; returns
    the ids where something changed."""
    p = os.path.join(profile, "extension-preferences.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    changed = []
    for i in ids:
        e = d.get(i) or {"permissions": [], "origins": [], "data_collection": []}
        perms = e.setdefault("permissions", [])
        if allow and PB not in perms:
            perms.append(PB)
            changed.append(i)
        elif not allow and PB in perms:
            perms.remove(PB)
            changed.append(i)
        if perms or e.get("origins") or e.get("data_collection"):
            d[i] = e
        else:
            d.pop(i, None)
    json.dump(d, open(p, "w"))
    return changed


def shortcuts(profile, states):
    """Sets the "disabled" flag of Zen's shortcuts (id -> bool); returns the previous ones."""
    p = os.path.join(profile, "zen-keyboard-shortcuts.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p))
    old = {}
    for sc in d.get("shortcuts", []):
        if sc.get("id") in states:
            old[sc["id"]] = sc.get("disabled", False)
            sc["disabled"] = states[sc["id"]]
    json.dump(d, open(p, "w"), separators=(",", ":"))
    return old


def apply(profile):
    st = os.path.join(profile, STATE)
    cur = read(profile)
    keys = list(PREFS) + ["browser.uiCustomization.state"]
    if not os.path.exists(st):
        saved = {"prefs": {k: cur.get(k) for k in keys}}
        saved["menubar_autohide"] = xulstore(profile, "false")
    else:
        # (from an earlier version: the new preferences are saved too)
        saved = json.load(open(st))
        for k in keys:
            saved["prefs"].setdefault(k, cur.get(k))
        xulstore(profile, "false")
    saved["private"] = sorted(set(saved.get("private", [])) | set(private_windows(profile, PRIVATE, True)))
    for k, v in shortcuts(profile, {i: True for i in SHORTCUTS_OFF}).items():
        saved.setdefault("shortcuts", {}).setdefault(k, v)
    json.dump(saved, open(st, "w"), indent=1)
    changes = dict(PREFS)
    changes["browser.uiCustomization.state"] = placements(cur.get("browser.uiCustomization.state"))
    write(profile, changes)


def undo(profile):
    st = os.path.join(profile, STATE)
    if not os.path.exists(st):
        return
    saved = json.load(open(st))
    write(profile, saved["prefs"])
    xulstore(profile, saved.get("menubar_autohide"))
    private_windows(profile, saved.get("private", []), False)
    shortcuts(profile, saved.get("shortcuts", {}))
    os.remove(st)


if __name__ == "__main__":
    {"apply": apply, "undo": undo}[sys.argv[1]](sys.argv[2])
