/*
 * Barra Favoritos do IE6: os marcadores do Zen como favoritos. A pasta
 * "Hiperligações" é a barra de marcadores (como no IE: a barra Hiperligações);
 * o resto do menu de marcadores aparece na raiz; "Outros favoritos" se houver.
 * Pastas primeiro, depois os endereços (pela ordem guardada).
 */
const ROOT_MENU = "menu________", ROOT_BAR = "toolbar_____", ROOT_OTHER = "unfiled_____";
const ICON_FOLDER = "img/folder.png", ICON_FOLDER_OPEN = "img/folder-open.png", ICON_PAGE = "img/page.png";

let topItems = [];

async function load() {
    const [tree] = await browser.bookmarks.getTree();
    const root = id => tree.children.find(c => c.id === id);
    const menu = root(ROOT_MENU), bar = root(ROOT_BAR), other = root(ROOT_OTHER);
    topItems = [];
    if (bar)
        topItems.push({...bar, title: "Hiperligações"});
    if (other && other.children && other.children.length)
        topItems.push({...other, title: "Outros favoritos"});
    topItems.push(...((menu && menu.children) || []));
    render();
}

function sorted(items) {
    const nodes = items.filter(n => n.type !== "separator");
    return [...nodes.filter(n => n.type === "folder"), ...nodes.filter(n => n.type !== "folder")];
}

function render() {
    const scroll = list.scrollTop;
    list.textContent = "";
    const add = (items, depth) => {
        for (const n of sorted(items)) {
            if (n.type === "folder") {
                const isOpen = openFolders.has(n.id);
                const r = row(depth, isOpen ? ICON_FOLDER_OPEN : ICON_FOLDER, n.title || "(sem nome)", n.id);
                r.dataset.folder = "1";
                list.append(r);
                if (isOpen)
                    add(n.children || [], depth + 1);
            } else {
                const r = row(depth, ICON_PAGE, n.title || n.url, n.id);
                r.dataset.url = n.url;
                list.append(r);
            }
        }
    };
    add(topItems, 0);
    if (!list.children.length) {
        const e = document.createElement("div");
        e.className = "empty";
        e.textContent = "Não há favoritos.";
        list.append(e);
    }
    list.scrollTop = scroll;
}

list.addEventListener("click", e => {
    const r = e.target.closest(".row");
    if (!r)
        return;
    select(r);
    if (r.querySelector("input"))
        return;
    if (r.dataset.folder) {
        toggleFolder(r.dataset.id);
        render();
    } else if (r.dataset.url) {
        openUrl(r.dataset.url, e);
    }
});

// botão direito: o menu de marcadores do próprio Zen (abrir, editar, eliminar...)
list.addEventListener("contextmenu", e => {
    const r = e.target.closest(".row");
    if (!r)
        return;
    select(r);
    browser.menus.overrideContext({context: "bookmark", bookmarkId: r.dataset.id});
});

list.addEventListener("keydown", e => {
    if (e.key === "Delete")
        removeSelected();
    else if (e.key === "F2")
        renameSelected();
});

// --- Adicionar... ----------------------------------------------------------
// abre a janela "Adicionar aos Favoritos" (como o IE), para a página atual
document.getElementById("add").addEventListener("click", async () => {
    const [tab] = await browser.tabs.query({active: true, currentWindow: true});
    if (!tab || !/^(https?|ftp|file):/.test(tab.url))
        return;
    const win = await browser.windows.getCurrent();
    const width = 420, height = 172;
    await browser.windows.create({
        url: `addfavorite.html?${new URLSearchParams({url: tab.url, title: tab.title || ""})}`,
        type: "popup",
        width,
        height,
        left: Math.round(win.left + (win.width - width) / 2),
        top: Math.round(win.top + (win.height - height) / 3),
    });
});

// --- Organizar... -----------------------------------------------------------
const orgbox = document.getElementById("orgbox");
document.getElementById("organize").addEventListener("click", () => {
    orgbox.hidden = !orgbox.hidden;
    document.getElementById("organize").classList.toggle("on", !orgbox.hidden);
});
document.getElementById("orgclose").addEventListener("click", () => {
    orgbox.hidden = true;
    document.getElementById("organize").classList.remove("on");
});

function selectedRow() {
    return selected ? list.querySelector(`.row[data-id="${CSS.escape(selected)}"]`) : null;
}

document.getElementById("newfolder").addEventListener("click", async () => {
    const r = selectedRow();
    let parentId = ROOT_MENU;
    if (r && r.dataset.folder)
        parentId = r.dataset.id;
    const f = await browser.bookmarks.create({parentId, title: "Nova pasta"});
    if (parentId !== ROOT_MENU) {
        openFolders.add(parentId);
        saveOpen();
    }
    selected = f.id;
    await load();
    renameSelected();
});
document.getElementById("rename").addEventListener("click", renameSelected);
document.getElementById("delete").addEventListener("click", removeSelected);

function renameSelected() {
    const r = selectedRow();
    if (!r || [ROOT_BAR, ROOT_OTHER].includes(r.dataset.id))
        return;
    const span = r.querySelector("span");
    const input = document.createElement("input");
    input.value = span.textContent;
    span.replaceWith(input);
    input.focus();
    input.select();
    let done = false;
    const finish = async save => {
        if (done)
            return;
        done = true;
        if (save && input.value.trim())
            await browser.bookmarks.update(r.dataset.id, {title: input.value.trim()});
        render();
        list.focus();
    };
    input.addEventListener("keydown", e => {
        if (e.key === "Enter")
            finish(true);
        else if (e.key === "Escape")
            finish(false);
        e.stopPropagation();
    });
    input.addEventListener("blur", () => finish(true));
}

async function removeSelected() {
    const r = selectedRow();
    if (!r || [ROOT_BAR, ROOT_OTHER].includes(r.dataset.id))
        return;
    const what = r.dataset.folder ? "a pasta" : "o favorito";
    if (!confirm(`Tem a certeza de que pretende eliminar ${what} "${r.querySelector("span").textContent}"?`))
        return;
    if (r.dataset.folder)
        await browser.bookmarks.removeTree(r.dataset.id);
    else
        await browser.bookmarks.remove(r.dataset.id);
    selected = null;
}

for (const ev of ["onCreated", "onRemoved", "onChanged", "onMoved"])
    browser.bookmarks[ev].addListener(() => load());
load();
