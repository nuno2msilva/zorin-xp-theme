/* Zorin XP — barras de deslocamento do XP.
 *
 * Regista chrome/zorin-xp-ie/scrollbars.css (gerado por tools/builders/zenie.py a
 * partir de src/zen-ie/scrollbars.css.in, com as imagens embutidas) como
 * folha de nível "agent": é o único nível que chega às peças das barras
 * (scrollbar, slider, thumb, scrollbarbutton) — o userContent.css só muda as
 * cores. Vale para todas as páginas e para a própria janela. */
"use strict";

/* global ExtensionAPI, Services, Cc, Ci */
this.zxpScrollbars = class extends ExtensionAPI {
  onStartup() {
    const file = Services.dirsvc.get("ProfD", Ci.nsIFile);
    for (const part of ["chrome", "zorin-xp-ie", "scrollbars.css"]) {
      file.append(part);
    }
    if (!file.exists()) {
      return;
    }
    this.uri = Services.io.newFileURI(file);
    this.sss = Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService);
    if (!this.sss.sheetRegistered(this.uri, this.sss.AGENT_SHEET)) {
      this.sss.loadAndRegisterSheet(this.uri, this.sss.AGENT_SHEET);
    }
  }

  onShutdown() {
    if (this.uri && this.sss.sheetRegistered(this.uri, this.sss.AGENT_SHEET)) {
      this.sss.unregisterSheet(this.uri, this.sss.AGENT_SHEET);
    }
  }

  getAPI() {
    return { zxpScrollbars: {} };
  }
};
