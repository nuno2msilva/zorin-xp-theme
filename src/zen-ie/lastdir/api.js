/* Zorin XP — the "Save As" folder remembered per site, not globally.
 *
 * Zen (DownloadLastDir) stores the folder where something was saved twice:
 * per site (content-prefs, per domain) and in a global preference,
 * browser.download.lastDir, which is the fallback for sites where nothing
 * was saved yet. Deleting the global one right after every save leaves only
 * the per-site memory; on a new site Zen suggests the downloads folder
 * (Downloads.getPreferredDownloadsDirectory), which is where the dialog
 * opens. Private windows use a session-only memory and do not change. */
"use strict";

/* global ExtensionAPI, Services */
// (the privileged scripts of one extension share a global: each keeps
// its names inside this block, only the API class goes out)
{
  const FEATURE = "extensions.zorin-xp-ie.lastdir";
  const PREF = "browser.download.lastDir";

  this.zxpLastDir = class extends ExtensionAPI {
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
      this.clear = () => {
        // (after Zen has finished saving: the site's one is written before)
        Services.tm.dispatchToMainThread(() => {
          if (Services.prefs.prefHasUserValue(PREF)) {
            Services.prefs.clearUserPref(PREF);
          }
        });
      };
      Services.prefs.addObserver(PREF, this.clear);
      this.clear();
    }

    stop() {
      if (this.clear) {
        Services.prefs.removeObserver(PREF, this.clear);
        this.clear = null;
      }
    }

    getAPI() {
      return { zxpLastDir: {} };
    }
  };
}
