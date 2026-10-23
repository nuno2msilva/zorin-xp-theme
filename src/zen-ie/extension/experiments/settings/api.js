/* Zorin XP — the features the Preferences page turns on and off.
 *
 * Each feature is a Zen preference, extensions.zorin-xp-ie.<name> (true by
 * default): the privileged parts (experiments/*) read it on startup, before
 * any window draws, and follow its changes; the background and the pages
 * use this API (get, set, onChanged). */
"use strict";

/* global ExtensionAPI, ChromeUtils, Services */
// (the privileged scripts of one extension share a global: each keeps
// its names inside this block, only the API class goes out)
{
  const { ExtensionCommon } = ChromeUtils.importESModule("resource://gre/modules/ExtensionCommon.sys.mjs");
  const BRANCH = "extensions.zorin-xp-ie.";
  const FEATURES = ["favorites", "history", "find", "sounds", "title", "scrollbars",
                    "sidebarpin", "tabflash", "lastdir"];

  function read() {
    const out = {};
    for (const name of FEATURES) {
      out[name] = Services.prefs.getBoolPref(BRANCH + name, true);
    }
    return out;
  }

  this.zxpSettings = class extends ExtensionAPI {
    getAPI(context) {
      return {
        zxpSettings: {
          async get() {
            return read();
          },
          async set(name, value) {
            if (!FEATURES.includes(name)) {
              throw new context.cloneScope.Error(`Funcionalidade desconhecida: ${name}`);
            }
            Services.prefs.setBoolPref(BRANCH + name, !!value);
          },
          onChanged: new ExtensionCommon.EventManager({
            context,
            name: "zxpSettings.onChanged",
            register: fire => {
              const observer = (_subject, _topic, pref) => {
                const name = pref.slice(BRANCH.length);
                if (FEATURES.includes(name)) {
                  fire.async(name, Services.prefs.getBoolPref(pref, true));
                }
              };
              Services.prefs.addObserver(BRANCH, observer);
              return () => Services.prefs.removeObserver(BRANCH, observer);
            },
          }).api(),
        },
      };
    }
  };
}
