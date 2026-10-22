// O botão "Favoritos" da barra abre e fecha a barra Favoritos (como no IE)
browser.browserAction.onClicked.addListener(() => browser.sidebarAction.toggle());
