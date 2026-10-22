#!/usr/bin/env python3
"""Preferências do Zen para o aspeto do Internet Explorer (src/zen-ie).

  apply <perfil>   botões do IE na barra de navegação (Página inicial,
                   Procurar, Favoritos, Histórico), userChrome.css ligado,
                   moldura do sistema (a barra de título XP), barra de menus
                   sempre visível, a janela Localizar autorizada em janelas
                   privadas e o Ctrl+F do Zen desligado (fica o da janela
                   Localizar). Guarda os valores antigos em
                   <perfil>/zorin-xp-ie.json.
  undo <perfil>    repõe os valores guardados.

O Zen tem de estar fechado (escreve no prefs.js à saída).
"""
import json
import os
import re
import sys

# (também corre sozinho: tools/ no caminho, para "from lib import ...")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Favoritos e Histórico: os botões das extensões das barras do Explorador
FAVORITES = "zorin-xp-ie-favorites_zorin-xp_local-browser-action"
HISTORY = "zorin-xp-ie-history_zorin-xp_local-browser-action"
FIND = "zorin-xp-ie-find_zorin-xp_local-browser-action"       # Procurar: a janela Localizar
NAV = ["back-button", "forward-button", "stop-reload-button", "home-button",
       FIND, FAVORITES, HISTORY]
REPLACED = ["bookmarks-menu-button", "history-panelmenu", "find-button"]   # (os de antes: tirados)
PREFS = {
    "toolkit.legacyUserProfileCustomizations.stylesheets": True,
    "browser.tabs.inTitlebar": 0,
    "zen.view.use-single-toolbar": False,
    # endereço completo na caixa, como o IE ("https://" incluído)
    "browser.urlbar.trimURLs": False,
    "browser.urlbar.trimHttps": False,
    # modo compacto: esconde só a barra lateral (as barras do IE ficam)
    "zen.view.compact.hide-toolbar": False,
    "zen.view.compact.hide-tabbar": True,
    # ao abrir, volta à última página vista (o Zen escolhia um separador vazio)
    "zen.workspaces.continue-where-left-off": True,
    # mudar de espaço troca logo os separadores e o nome, sem deslizar
    "zen.workspaces.switch-animation-duration": 0,
    # sem o aviso "Novo separador aberto em segundo plano!" (o IE não o tinha)
    "zen.view.compact.show-background-tab-toast": False,
    # ao abrir, a caixa de endereço fica fechada (o Zen abria-a com a lista
    # de sugestões quando o separador inicial está vazio)
    "zen.urlbar.open-on-startup": False,
    # a extensão dos sons do IE (local, sem assinatura da Mozilla), posta na
    # pasta extensions do perfil: ativa sem pedir confirmação
    "xpinstall.signatures.required": False,
    "extensions.autoDisableScopes": 14,
    # (a da pasta por sítio usa uma API experimental: o Zen deixa por omissão)
    "extensions.experiments.enabled": True,
    # barras de deslocamento das páginas como as do XP: sempre à vista, 17 px,
    # com as setas em cima e em baixo (as imagens do Luna vêm da extensão
    # src/zen-ie/scrollbars; o userContent.css só dá as cores de reserva)
    "widget.gtk.overlay-scrollbars.enabled": False,
    "widget.non-native-theme.scrollbar.style": 4,
    "ui.scrollArrowStyle": 4097,
    # (as finas que alguns sítios pedem ficam normais, como no XP)
    "layout.css.scrollbar-width-thin.disabled": True,
}
# a janela Localizar fica pronta numa janela privada (ver src/zen-ie/find)
PRIVATE = ["zorin-xp-ie-find@zorin-xp.local"]
PB = "internal:privateBrowsingAllowed"
# atalhos do Zen desligados: o Ctrl+F passa a ser o da janela Localizar
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
    """Dá (ou tira) a permissão de correr em janelas privadas; devolve os ids
    em que mudou alguma coisa."""
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
    """Põe o "disabled" dos atalhos do Zen (id -> bool); devolve os de antes."""
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
        # (de uma versão anterior: guardam-se também as preferências novas)
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
