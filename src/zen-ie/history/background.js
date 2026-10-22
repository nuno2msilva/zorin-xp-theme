// O botão "Histórico" da barra abre e fecha a barra Histórico (como no IE)
browser.browserAction.onClicked.addListener(() => browser.sidebarAction.toggle());
