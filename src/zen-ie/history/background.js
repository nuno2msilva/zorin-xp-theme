// The toolbar's "Histórico" button opens and closes the History bar (as in IE)

browser.browserAction.onClicked.addListener(() => browser.sidebarAction.toggle());
