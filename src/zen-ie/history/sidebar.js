/*
 * IE6's History bar. Views of the "View" button:
 *   By date       — "Há 3 semanas", "Há 2 semanas", "Há 1 semana", this
 *                   week's days by name and "Hoje" (at the end, as in IE),
 *                   each with a folder per site and the pages inside
 *   By site       — a folder per site
 *   By most visited / By order visited today — a plain list
 * "Search" shows only the pages that contain the text.
 */
const DAY = 86400000;
const ICON_DAY = "img/history-day.png", ICON_FOLDER = "img/folder.png",
    ICON_FOLDER_OPEN = "img/folder-open.png", ICON_PAGE = "img/page.png";
const WEEKDAYS = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado"];

let view = localStorage.getItem("view") || "date";
let query = "";
let items = [];

function host(url) {
    try {
        const u = new URL(url);
        return u.hostname || u.protocol.replace(":", "");
    } catch (e) {
        return url;
    }
}

function dayGroup(t) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if (t >= today)
        return {key: "0", name: "Hoje"};
    // this week's days (since Monday) by name
    const dow = (now.getDay() + 6) % 7;            // 0 = segunda
    const monday = today - dow * DAY;
    if (t >= monday) {
        const d = new Date(t);
        return {key: String(Math.ceil((today - t) / DAY)), name: WEEKDAYS[d.getDay()]};
    }
    const weeks = Math.min(3, Math.floor((monday - t) / (7 * DAY)) + 1);
    return {key: String(100 + weeks), name: weeks === 1 ? "Há 1 semana" : `Há ${weeks} semanas`};
}

async function load() {
    items = await browser.history.search({
        text: query, startTime: Date.now() - 28 * DAY, maxResults: 5000,
    });
    render();
}

function pageRow(depth, it, id) {
    const r = row(depth, ICON_PAGE, it.title || it.url, id);
    r.dataset.url = it.url;
    r.title = it.url;
    return r;
}

function addSites(pages, depth, prefix) {
    const sites = new Map();
    for (const it of pages) {
        const h = host(it.url);
        if (!sites.has(h))
            sites.set(h, []);
        sites.get(h).push(it);
    }
    for (const h of [...sites.keys()].sort()) {
        const id = `${prefix}|${h}`;
        const isOpen = openFolders.has(id);
        const r = row(depth, isOpen ? ICON_FOLDER_OPEN : ICON_FOLDER, h, id);
        r.dataset.folder = "1";
        list.append(r);
        if (isOpen) {
            const ps = sites.get(h).sort((a, b) => (a.title || a.url).localeCompare(b.title || b.url));
            for (const it of ps)
                list.append(pageRow(depth + 1, it, `${id}|${it.url}`));
        }
    }
}

function render() {
    const scroll = list.scrollTop;
    list.textContent = "";
    for (const d of document.querySelectorAll("#viewmenu > div"))
        d.classList.toggle("on", d.dataset.view === view);
    if (query) {
        for (const it of [...items].sort((a, b) => b.lastVisitTime - a.lastVisitTime))
            list.append(pageRow(0, it, `q|${it.url}`));
    } else if (view === "date") {
        const groups = new Map();
        for (const it of items) {
            const g = dayGroup(it.lastVisitTime);
            if (!groups.has(g.key))
                groups.set(g.key, {name: g.name, pages: []});
            groups.get(g.key).pages.push(it);
        }
        // from oldest to newest: "Hoje" at the end, as in IE6
        const keys = [...groups.keys()].sort((a, b) => Number(b) - Number(a));
        for (const k of keys) {
            const id = `d|${k}`;
            const r = row(0, ICON_DAY, groups.get(k).name, id);
            r.dataset.folder = "1";
            list.append(r);
            if (openFolders.has(id))
                addSites(groups.get(k).pages, 1, id);
        }
    } else if (view === "site") {
        addSites(items, 0, "s");
    } else if (view === "most") {
        for (const it of [...items].sort((a, b) => (b.visitCount || 0) - (a.visitCount || 0)))
            list.append(pageRow(0, it, `m|${it.url}`));
    } else {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        for (const it of items.filter(x => x.lastVisitTime >= today).sort((a, b) => b.lastVisitTime - a.lastVisitTime))
            list.append(pageRow(0, it, `t|${it.url}`));
    }
    if (!list.children.length) {
        const e = document.createElement("div");
        e.className = "empty";
        e.textContent = query ? "Não foram encontrados itens." : "O histórico está vazio.";
        list.append(e);
    }
    list.scrollTop = scroll;
}

list.addEventListener("click", e => {
    const r = e.target.closest(".row");
    if (!r)
        return;
    select(r);
    if (r.dataset.folder) {
        toggleFolder(r.dataset.id);
        render();
    } else if (r.dataset.url) {
        openUrl(r.dataset.url, e);
    }
});

list.addEventListener("keydown", async e => {
    const r = selected && list.querySelector(".row.sel");
    if (e.key === "Delete" && r && r.dataset.url) {
        await browser.history.deleteUrl({url: r.dataset.url});
        load();
    }
});

// --- View ---------------------------------------------------------------------
const viewmenu = document.getElementById("viewmenu");
const viewbtn = document.getElementById("view");
viewbtn.addEventListener("click", e => {
    e.stopPropagation();
    viewmenu.hidden = !viewmenu.hidden;
    viewbtn.classList.toggle("on", !viewmenu.hidden);
    const b = viewbtn.getBoundingClientRect();
    viewmenu.style.left = `${b.left}px`;
    viewmenu.style.top = `${b.bottom}px`;
});
viewmenu.addEventListener("click", e => {
    const d = e.target.closest("div[data-view]");
    if (!d)
        return;
    view = d.dataset.view;
    localStorage.setItem("view", view);
    query = "";
    document.getElementById("query").value = "";
    viewmenu.hidden = true;
    viewbtn.classList.remove("on");
    load();
});
document.addEventListener("click", () => {
    viewmenu.hidden = true;
    viewbtn.classList.remove("on");
});

// --- Procurar -----------------------------------------------------------------
const searchbox = document.getElementById("searchbox");
const searchbtn = document.getElementById("search");
const queryInput = document.getElementById("query");
searchbtn.addEventListener("click", () => {
    searchbox.hidden = !searchbox.hidden;
    searchbtn.classList.toggle("on", !searchbox.hidden);
    if (searchbox.hidden) {
        query = "";
        load();
    } else {
        queryInput.focus();
    }
});
function searchNow() {
    query = queryInput.value.trim();
    load();
}
document.getElementById("searchnow").addEventListener("click", searchNow);
queryInput.addEventListener("keydown", e => {
    if (e.key === "Enter")
        searchNow();
});

browser.history.onVisited.addListener(() => load());
browser.history.onVisitRemoved.addListener(() => load());
load();
