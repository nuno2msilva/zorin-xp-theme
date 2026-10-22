/*
 * Comum às barras Favoritos e Histórico: linhas da lista (ícone + texto,
 * recuo por nível), seleção, pastas que abrem com um clique (como no IE) e
 * abrir endereços (clique: no separador atual; botão do meio ou Ctrl: novo).
 */
const list = document.getElementById("list");
let selected = null;           // id do item seleccionado

// pastas abertas (guardadas entre aberturas da barra)
const openFolders = new Set(JSON.parse(localStorage.getItem("open") || "[]"));
function saveOpen() {
    localStorage.setItem("open", JSON.stringify([...openFolders]));
}

function row(depth, icon, text, id) {
    const r = document.createElement("div");
    r.className = "row";
    r.style.setProperty("--depth", depth);
    r.dataset.id = id;
    const img = document.createElement("img");
    img.src = icon;
    const span = document.createElement("span");
    span.textContent = text;
    r.append(img, span);
    if (id === selected)
        r.classList.add("sel");
    r.title = text;
    return r;
}

function select(r) {
    for (const s of list.querySelectorAll(".row.sel"))
        s.classList.remove("sel");
    if (r) {
        r.classList.add("sel");
        selected = r.dataset.id;
    } else {
        selected = null;
    }
}

function openUrl(url, event) {
    if (event && (event.button === 1 || event.ctrlKey))
        browser.tabs.create({url, active: false});
    else
        browser.tabs.update({url});
}

function toggleFolder(id) {
    if (openFolders.has(id))
        openFolders.delete(id);
    else
        openFolders.add(id);
    saveOpen();
}

// botão do meio: abrir num separador novo
list.addEventListener("auxclick", e => {
    if (e.button !== 1)
        return;
    const r = e.target.closest(".row");
    if (r && r.dataset.url)
        openUrl(r.dataset.url, e);
});
list.addEventListener("mousedown", e => {
    if (e.button === 1)
        e.preventDefault();       // (sem rolagem automática)
});
