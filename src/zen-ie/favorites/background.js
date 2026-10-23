// The toolbar's "Favoritos" button opens and closes the Favorites bar (as in IE)
browser.browserAction.onClicked.addListener(() => browser.sidebarAction.toggle());
