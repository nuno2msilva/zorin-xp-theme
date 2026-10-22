/* Zorin XP — aviso de novo separador no modo compacto.
 *
 * Quando se abre um separador em segundo plano (ex.: clique do meio numa
 * ligação), a janela fica com o atributo zxp-tab-flash e o separador com
 * zxp-flash durante a animação; o userChrome (src/zen-ie/ie.css) desenha a
 * faixa laranja a piscar na beira esquerda (modo compacto: a barra dos
 * separadores está escondida) e o separador a piscar como um botão da barra
 * de tarefas do XP (barra lateral à vista). Feito aqui, e
 * não só em CSS, porque o CSS voltava a piscar ao arrancar (separadores
 * restaurados) e ao mudar de espaço (separadores que voltam a ser mostrados). */
"use strict";

/* global ExtensionAPI, ChromeUtils, Services */
const { setTimeout, clearTimeout } = ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");
const ATTR = "zxp-tab-flash";
const TAB_ATTR = "zxp-flash";
const FLASH_MS = 1100;

this.zxpTabFlash = class extends ExtensionAPI {
  onStartup() {
    this.windows = new Set();
    this.ready = false;
    // (os separadores repostos ao arrancar não contam)
    // (o módulo mudou de sítio no Firefox 158: o novo primeiro, o antigo depois)
    let SessionStore = null;
    for (const url of ["moz-src:///browser/components/sessionstore/SessionStore.sys.mjs",
                       "resource:///modules/sessionstore/SessionStore.sys.mjs"]) {
      try {
        ({ SessionStore } = ChromeUtils.importESModule(url));
        break;
      } catch (e) {}
    }
    if (SessionStore) {
      SessionStore.promiseAllWindowsRestored.then(() => {
        Services.tm.dispatchToMainThread(() => { this.ready = true; });
      });
    } else {
      this.ready = true;
    }

    // (os elementos chegam aqui embrulhados: as propriedades JS do separador
    // — selected, pinned, ownerGlobal — não se veem; usam-se os atributos)
    this.onTabOpen = (event, win) => {
      const tab = event.target;
      if (!this.ready || tab.hasAttribute("pinned") || tab.hasAttribute("pending")) {
        return;
      }
      // (um separador novo à frente já se vê: só os de segundo plano)
      win.setTimeout(() => {
        if (tab.isConnected && !tab.hasAttribute("selected") && !tab.hasAttribute("pending")) {
          this.flash(win, tab);
        }
      }, 0);
    };
    this.track = win => {
      if (this.windows.has(win) || !win.gBrowser) {
        return;
      }
      this.windows.add(win);
      win._zxpTabOpen = event => this.onTabOpen(event, win);
      win.addEventListener("TabOpen", win._zxpTabOpen);
      win.addEventListener("unload", () => this.windows.delete(win), { once: true });
    };
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      this.track(win);
    }
    this.observer = subject => this.track(subject);
    Services.obs.addObserver(this.observer, "browser-delayed-startup-finished");
    // (se a reposição da sessão nunca avisar, ao fim de 10 s já conta)
    this.readyTimer = setTimeout(() => { this.ready = true; }, 10000);
  }

  // a janela (faixa na beira, modo compacto) e o próprio separador (barra
  // lateral à vista) piscam juntos
  flash(win, tab) {
    const root = win.document.documentElement;
    root.removeAttribute(ATTR);
    root.getBoundingClientRect();         // (recomeça a animação)
    root.setAttribute(ATTR, "true");
    win.clearTimeout(win._zxpTabFlashTimer);
    win._zxpTabFlashTimer = win.setTimeout(() => root.removeAttribute(ATTR), FLASH_MS);
    tab.setAttribute(TAB_ATTR, "true");
    win.setTimeout(() => tab.removeAttribute(TAB_ATTR), FLASH_MS);
  }

  onShutdown() {
    clearTimeout(this.readyTimer);
    if (this.observer) {
      Services.obs.removeObserver(this.observer, "browser-delayed-startup-finished");
      this.observer = null;
    }
    for (const win of this.windows) {
      win.removeEventListener("TabOpen", win._zxpTabOpen);
      win.document.documentElement.removeAttribute(ATTR);
      for (const t of win.document.querySelectorAll(`[${TAB_ATTR}]`)) {
        t.removeAttribute(TAB_ATTR);
      }
    }
    this.windows.clear();
  }

  getAPI() {
    return { zxpTabFlash: {} };
  }
};
