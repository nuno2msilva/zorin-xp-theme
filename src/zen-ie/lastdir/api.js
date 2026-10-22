/* Zorin XP — a pasta do "Guardar como" lembrada por sítio, não global.
 *
 * O Zen (DownloadLastDir) guarda a pasta onde se gravou duas vezes: no sítio
 * (content-prefs, por domínio) e numa preferência global,
 * browser.download.lastDir, que serve de reserva aos sítios onde ainda não
 * se gravou nada. Apagando a global logo a seguir a cada gravação, fica só a
 * memória por sítio; num sítio novo o Zen propõe a pasta das transferências
 * (Downloads.getPreferredDownloadsDirectory), que é onde a janela abre.
 * As janelas privadas usam uma memória só da sessão e não mudam. */
"use strict";

/* global ExtensionAPI, Services */
const PREF = "browser.download.lastDir";

this.zxpLastDir = class extends ExtensionAPI {
  onStartup() {
    this.clear = () => {
      // (depois de o Zen acabar de gravar: a do sítio é escrita antes)
      Services.tm.dispatchToMainThread(() => {
        if (Services.prefs.prefHasUserValue(PREF)) {
          Services.prefs.clearUserPref(PREF);
        }
      });
    };
    Services.prefs.addObserver(PREF, this.clear);
    this.clear();
  }

  onShutdown() {
    if (this.clear) {
      Services.prefs.removeObserver(PREF, this.clear);
      this.clear = null;
    }
  }

  getAPI() {
    return { zxpLastDir: {} };
  }
};
