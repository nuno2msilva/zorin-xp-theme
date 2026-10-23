/* Zorin XP — the tab bar pin.
 *
 * Puts a button (#zxp-sidebar-pin) inside the sidebar of each window;
 * userChrome (src/zen-ie/ie.css) places it to the right of the space's
 * title, like the pin of XP's Explorer bars (Luna's ExplorerBar.HeaderPin),
 * and picks the image by mode: pushed in = pinned bar, lying = compact mode.
 * The click is Zen's own command (cmd_zenCompactModeToggle, Ctrl+S). */
"use strict";

/* global ExtensionAPI, Services */
// (the privileged scripts of one extension share a global: each keeps
// its names inside this block, only the API class goes out)
{
  const FEATURE = "extensions.zorin-xp-ie.sidebarpin";
  const ID = "zxp-sidebar-pin";
  // (the "Ocultar automaticamente" (Auto-hide) of XP's taskbar, explorer.exe)
  const TIP_HIDE = "Ocultar automaticamente";
  const TIP_PIN = "Afixar a barra";

  this.zxpSidebarPin = class extends ExtensionAPI {
    // turned on and off by the Preferences page, at once (the Zen preference
    // FEATURE, extensions.zorin-xp-ie.*, true by default)
    onStartup() {
      this.toggle = () => {
        const on = Services.prefs.getBoolPref(FEATURE, true);
        if (on !== !!this.running) {
          this.running = on;
          if (on) {
            this.start();
          } else {
            this.stop();
          }
        }
      };
      Services.prefs.addObserver(FEATURE, this.toggle);
      this.toggle();
    }

    onShutdown() {
      Services.prefs.removeObserver(FEATURE, this.toggle);
      if (this.running) {
        this.running = false;
        this.stop();
      }
    }

    start() {
      this.windows = new Set();
      this.track = win => {
        if (this.windows.has(win) || !win.gBrowser) {
          return;
        }
        const doc = win.document;
        const toolbox = doc.getElementById("navigator-toolbox");
        const cmd = doc.getElementById("cmd_zenCompactModeToggle");
        if (!toolbox || !cmd || doc.getElementById(ID)) {
          return;
        }
        this.windows.add(win);
        const button = doc.createXULElement("toolbarbutton");
        button.id = ID;
        button.addEventListener("command", () => cmd.doCommand());
        // (the tooltip says what the click will do)
        button.addEventListener("mouseover", () => {
          const compact = doc.documentElement.getAttribute("zen-compact-mode") == "true";
          button.setAttribute("tooltiptext", compact ? TIP_PIN : TIP_HIDE);
        });
        toolbox.append(button);
        win.addEventListener("unload", () => this.windows.delete(win), { once: true });
      };
      for (const win of Services.wm.getEnumerator("navigator:browser")) {
        this.track(win);
      }
      this.observer = subject => this.track(subject);
      Services.obs.addObserver(this.observer, "browser-delayed-startup-finished");
    }

    stop() {
      if (this.observer) {
        Services.obs.removeObserver(this.observer, "browser-delayed-startup-finished");
        this.observer = null;
      }
      for (const win of this.windows) {
        win.document.getElementById(ID)?.remove();
      }
      this.windows.clear();
    }

    getAPI() {
      return { zxpSidebarPin: {} };
    }
  };
}
