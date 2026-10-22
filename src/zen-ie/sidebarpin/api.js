/* Zorin XP — pino da barra dos separadores.
 *
 * Põe em cada janela um botão (#zxp-sidebar-pin) dentro da barra lateral; o
 * userChrome (src/zen-ie/ie.css) coloca-o à direita do título do espaço, como
 * o pino das barras do Explorador do XP (ExplorerBar.HeaderPin do Luna), e
 * escolhe a imagem pelo modo: espetado = barra fixa, deitado = modo compacto.
 * O clique é o comando do próprio Zen (cmd_zenCompactModeToggle, o Ctrl+S). */
"use strict";

/* global ExtensionAPI, Services */
const ID = "zxp-sidebar-pin";
// (o "Ocultar automaticamente" da barra de tarefas do XP, explorer.exe)
const TIP_HIDE = "Ocultar automaticamente";
const TIP_PIN = "Afixar a barra";

this.zxpSidebarPin = class extends ExtensionAPI {
  onStartup() {
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
      // (a dica diz o que o clique vai fazer)
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

  onShutdown() {
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
