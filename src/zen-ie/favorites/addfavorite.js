/*
 * "Adicionar aos Favoritos" (opened by the Favorites bar's Add...): the
 * page's name, and "Criar em >>" shows the folders (with "Nova pasta...").
 */
const params = new URLSearchParams(location.search);
const url = params.get("url");
const nameInput = document.getElementById("name");
const more = document.getElementById("more");
const tree = document.getElementById("tree");
const newfolder = document.getElementById("newfolder");
const ROOT_MENU = "menu________", ROOT_BAR = "toolbar_____", ROOT_OTHER = "unfiled_____";
let target = ROOT_MENU;
const open = new Set([ROOT_MENU]);

nameInput.value = params.get("title") || url;
nameInput.select();

async function renderTree() {
    const [root] = await browser.bookmarks.getTree();
    const byId = id => root.children.find(c => c.id === id);
    const menu = byId(ROOT_MENU), bar = byId(ROOT_BAR), other = byId(ROOT_OTHER);
    tree.textContent = "";
    const add = (node, title, depth) => {
        const r = document.createElement("div");
        r.className = "row" + (node.id === target ? " sel" : "");
        r.style.setProperty("--depth", depth);
        r.dataset.id = node.id;
        const img = document.createElement("img");
        img.src = open.has(node.id) ? "img/folder-open.png" : "img/folder.png";
        const span = document.createElement("span");
        span.textContent = title;
        r.append(img, span);
        tree.append(r);
        if (open.has(node.id))
            for (const c of (node.children || []).filter(n => n.type === "folder"))
                add(c, c.title, depth + 1);
    };
    // the root is "Favoritos" (the bookmarks menu), with "Hiperligações" (the toolbar)
    const rootNode = {...menu, children: [{...bar, title: "Hiperligações"},
        ...(other && other.children && other.children.length ? [{...other, title: "Outros favoritos"}] : []),
        ...(menu.children || [])]};
    add(rootNode, "Favoritos", 0);
}

tree.addEventListener("click", e => {
    const r = e.target.closest(".row");
    if (!r)
        return;
    target = r.dataset.id;
    if (open.has(target) && target !== ROOT_MENU)
        open.delete(target);
    else
        open.add(target);
    renderTree();
});

async function resize(expanded) {
    const win = await browser.windows.getCurrent();
    await browser.windows.update(win.id, {height: expanded ? 360 : 172});
}

document.getElementById("createin").addEventListener("click", async e => {
    more.hidden = !more.hidden;
    newfolder.hidden = more.hidden;
    e.target.textContent = more.hidden ? "Criar em >>" : "Criar em <<";
    if (!more.hidden)
        await renderTree();
    resize(!more.hidden);
});

newfolder.addEventListener("click", async () => {
    const f = await browser.bookmarks.create({parentId: target, title: "Nova pasta"});
    open.add(target);
    target = f.id;
    await renderTree();
    const r = tree.querySelector(".row.sel");
    const span = r.querySelector("span");
    const input = document.createElement("input");
    input.value = "Nova pasta";
    span.replaceWith(input);
    input.focus();
    input.select();
    const done = async () => {
        if (input.value.trim())
            await browser.bookmarks.update(f.id, {title: input.value.trim()});
        renderTree();
    };
    input.addEventListener("blur", done, {once: true});
    input.addEventListener("keydown", e => {
        if (e.key === "Enter")
            input.blur();
        e.stopPropagation();
    });
});

async function ok() {
    if (url)
        await browser.bookmarks.create({parentId: target, title: nameInput.value || url, url});
    window.close();
}
document.getElementById("ok").addEventListener("click", ok);
document.getElementById("cancel").addEventListener("click", () => window.close());
document.addEventListener("keydown", e => {
    if (e.key === "Enter")
        ok();
    else if (e.key === "Escape")
        window.close();
});
