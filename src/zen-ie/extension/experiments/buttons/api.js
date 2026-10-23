/* Zorin XP — IE's Search, Favorites and History buttons.
 *
 * An extension has a single toolbar button (browser action), so the three
 * are made here, with the same inside as an extension's button (toolbaritem
 * > toolbarbutton.unified-extensions-item-action-button with the badge
 * stack): userChrome (src/zen-ie/ie.css) draws them as in IE6, as before.
 *
 * Favorites and History share the extension's one side bar, the Explorer
 * bar, as in IE6 (one bar at a time): the button of the bar that is open
 * closes it; the other one asks the background to put its page in the bar
 * (sidebarAction.setPanel), which then calls showBar. The window's
 * zxp-ebar attribute says which bar it is (the pressed button, in ie.css).
 * A feature turned off in the Preferences (extensions.zorin-xp-ie.*) hides
 * its button. */
"use strict";

/* global ExtensionAPI, ChromeUtils, Services */
// (the privileged scripts of one extension share a global: each keeps
// its names inside this block, only the API class goes out)
{
  const { ExtensionCommon } = ChromeUtils.importESModule("resource://gre/modules/ExtensionCommon.sys.mjs");

  function customizableUI() {
    // (the module moved to moz-src in newer Firefox versions: the new one first)
    for (const url of ["moz-src:///browser/components/customizableui/CustomizableUI.sys.mjs",
                       "resource:///modules/CustomizableUI.sys.mjs"]) {
      try {
        return ChromeUtils.importESModule(url).CustomizableUI;
      } catch (e) {}
    }
    return null;
  }

  const BRANCH = "extensions.zorin-xp-ie.";
  // widget id -> [feature, label]
  const BUTTONS = {
    "zxp-ie-search": ["find", "Procurar"],
    "zxp-ie-favorites": ["favorites", "Favoritos"],
    "zxp-ie-history": ["history", "Histórico"],
  };
  const BAR = { "zxp-ie-favorites": "favorites", "zxp-ie-history": "history" };

  this.zxpButtons = class extends ExtensionAPI {
    // (the side bar's command: the extension's id made into a widget id)
    get barCommand() {
      return `${this.extension.id.toLowerCase().replace(/[^a-z0-9_-]/g, "_")}-sidebar-action`;
    }

    barOpen(win) {
      const sc = win.wrappedJSObject.SidebarController;
      return !!sc && sc.isOpen && sc.currentID === this.barCommand;
    }

    onStartup() {
      this.listeners ??= new Set();
      this.cui = customizableUI();
      if (!this.cui) {
        return;
      }
      for (const [id, [feature, label]] of Object.entries(BUTTONS)) {
        this.cui.createWidget({
          id,
          type: "custom",
          label,
          removable: true,
          onBuild: doc => this.build(doc, id, feature, label),
        });
      }
      // a feature turned off: its button goes, and its bar closes
      this.prefObserver = (_subject, _topic, pref) => {
        const feature = pref.slice(BRANCH.length);
        const on = Services.prefs.getBoolPref(pref, true);
        for (const win of Services.wm.getEnumerator("navigator:browser")) {
          for (const [id, [f]] of Object.entries(BUTTONS)) {
            if (f === feature) {
              const node = win.document.getElementById(id);
              if (node) {
                node.hidden = !on;
              }
            }
          }
          if (!on && win.document.documentElement.getAttribute("zxp-ebar") === feature && this.barOpen(win)) {
            win.wrappedJSObject.SidebarController.hide();
          }
        }
      };
      Services.prefs.addObserver(BRANCH, this.prefObserver);
    }

    build(doc, id, feature, label) {
      const item = doc.createXULElement("toolbaritem");
      item.id = id;
      item.className = "toolbaritem-combined-buttons unified-extensions-item chromeclass-toolbar-additional";
      item.setAttribute("label", label);
      item.setAttribute("removable", "true");
      item.setAttribute("overflows", "true");
      item.hidden = !Services.prefs.getBoolPref(BRANCH + feature, true);
      const button = doc.createXULElement("toolbarbutton");
      button.className = "toolbarbutton-1 unified-extensions-item-action-button";
      button.setAttribute("badged", "true");
      button.setAttribute("label", label);
      button.setAttribute("tooltiptext", label);
      button.addEventListener("command", () => this.click(doc.defaultView, id));
      item.append(button);
      return item;
    }

    click(win, id) {
      const bar = BAR[id];
      // (the open bar's own button closes it, as in IE)
      if (bar && this.barOpen(win) && win.document.documentElement.getAttribute("zxp-ebar") === bar) {
        win.wrappedJSObject.SidebarController.hide();
        return;
      }
      const windowId = this.extension.windowManager.getWrapper(win)?.id;
      for (const fire of this.listeners ?? []) {
        fire(bar || "find", windowId);
      }
    }

    onShutdown(isAppShutdown) {
      if (this.prefObserver) {
        Services.prefs.removeObserver(BRANCH, this.prefObserver);
        this.prefObserver = null;
      }
      // (on quitting the buttons stay where they are; turned off or removed, they go)
      if (this.cui && !isAppShutdown) {
        for (const id of Object.keys(BUTTONS)) {
          this.cui.destroyWidget(id);
        }
      }
    }

    getAPI(context) {
      const window = id => this.extension.windowManager.get(id, context).window;
      return {
        zxpButtons: {
          showBar: async (windowId, bar) => {
            const win = window(windowId);
            win.document.documentElement.setAttribute("zxp-ebar", bar);
            if (!this.barOpen(win)) {
              win.wrappedJSObject.SidebarController.show(this.barCommand);
            }
          },
          // (Search turned off: Ctrl+F opens the browser's own find bar)
          nativeFind: async windowId => {
            const findbar = await window(windowId).wrappedJSObject.gBrowser.getFindBar();
            findbar.onFindCommand();
          },
          onClicked: new ExtensionCommon.EventManager({
            context,
            name: "zxpButtons.onClicked",
            register: fire => {
              const listener = (button, windowId) => fire.async(button, windowId);
              (this.listeners ??= new Set()).add(listener);
              return () => this.listeners.delete(listener);
            },
          }).api(),
        },
      };
    }
  };
}
