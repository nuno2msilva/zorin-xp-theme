/*
 * Find window: searches the active tab of the window it was called from (the
 * background says which: the window stays ready from one use to the next),
 * with browser.find (the browser's find: highlights and shows the result,
 * without touching the page). "Localizar seguinte" (Find Next) moves
 * through the results in the chosen direction; the search starts over when
 * the text or the options change.
 */
const q = document.getElementById("q");
const next = document.getElementById("next");
const whole = document.getElementById("wholeword");
const matchCase = document.getElementById("matchcase");

let state = null;          // {key, tabId, count, index}

async function activeTab() {
    const windowId = await browser.runtime.sendMessage({op: "parent"});
    if (windowId == null)
        return null;
    const [tab] = await browser.tabs.query({active: true, windowId});
    return tab;
}

function down() {
    return document.querySelector('input[name="dir"]:checked').value === "down";
}

async function findNext() {
    const text = q.value;
    if (!text)
        return;
    const tab = await activeTab();
    if (!tab)
        return;
    const key = JSON.stringify([text, whole.checked, matchCase.checked, tab.id, tab.url]);
    if (!state || state.key !== key) {
        const res = await browser.find.find(text, {
            tabId: tab.id, caseSensitive: matchCase.checked, entireWord: whole.checked,
        });
        state = {key, tabId: tab.id, count: res.count, index: down() ? -1 : res.count};
    }
    if (!state.count) {
        alert("Terminou a pesquisa do documento.");
        return;
    }
    state.index += down() ? 1 : -1;
    if (state.index >= state.count || state.index < 0) {
        // (like IE: warns and starts over from the other end)
        alert("Terminou a pesquisa do documento.");
        state.index = down() ? 0 : state.count - 1;
    }
    await browser.find.highlightResults({tabId: state.tabId, rangeIndex: state.index});
}

async function cancel() {
    if (state)
        await browser.find.removeHighlighting(state.tabId).catch(() => {});
    state = null;
    // (it stays ready for next time: the background hides it, or closes it)
    browser.runtime.sendMessage({op: "hide"});
}

// chamada outra vez (Procurar, Ctrl+F): o texto pronto a escrever por cima
function ready() {
    q.focus();
    q.select();
}
browser.runtime.onMessage.addListener(msg => {
    if (msg.op === "shown")
        ready();
});

q.addEventListener("input", () => (next.disabled = !q.value));
next.addEventListener("click", findNext);
document.getElementById("cancel").addEventListener("click", cancel);
document.addEventListener("keydown", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        findNext();
    } else if (e.key === "Escape") {
        cancel();
    }
});
for (const el of [whole, matchCase])
    el.addEventListener("change", () => (state = null));
ready();
