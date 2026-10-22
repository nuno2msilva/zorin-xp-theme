/*
 * "Procurar" e Ctrl+F: a janela Localizar (uma janela à parte, que se pode
 * mover, como no IE). Procura no separador ativo da janela de onde foi
 * chamada, com a procura do próprio browser (sem mexer na página).
 *
 * Abrir uma janela do browser leva o seu tempo, por isso a janela fica
 * pronta: depois da primeira vez, fechá-la (Cancelar, Esc, Procurar) só a
 * minimiza, e voltar a chamá-la é só restaurá-la. Fica numa janela privada,
 * que não conta para a sessão do Zen (que só se grava ao fechar a última
 * janela "regular"), e fecha-se quando já não há janelas normais. A extensão
 * do GNOME tira-a da barra de tarefas e do Alt+Tab. Sem a permissão das
 * janelas privadas, a janela fecha-se de verdade, como antes.
 */
const WIDTH = 384, HEIGHT = 152;
let find = null;          // {id, parent, keep}
let opening = null;

function placement(parent) {
    return {
        left: Math.round(parent.left + (parent.width - WIDTH) / 2),
        top: Math.round(parent.top + (parent.height - HEIGHT) / 3),
    };
}

// (no Zen o clique pode chegar sem o separador: a última janela focada)
async function parentOf(tab) {
    if (tab && (!find || tab.windowId !== find.id))
        return browser.windows.get(tab.windowId);
    if (find && find.parent)
        return browser.windows.get(find.parent).catch(() => browser.windows.getLastFocused({windowTypes: ["normal"]}));
    return browser.windows.getLastFocused({windowTypes: ["normal"]});
}

async function visible() {
    if (!find)
        return false;
    const w = await browser.windows.get(find.id).catch(() => null);
    return !!w && w.state !== "minimized";
}

async function show(parent) {
    if (find) {
        find.parent = parent.id;
        await browser.windows.update(find.id, {state: "normal", focused: true, ...placement(parent)});
        browser.runtime.sendMessage({op: "shown"}).catch(() => {});
        return;
    }
    const keep = await browser.extension.isAllowedIncognitoAccess();
    const win = await browser.windows.create({
        url: "find.html",
        type: "popup",
        incognito: keep,
        width: WIDTH,
        height: HEIGHT,
        ...placement(parent),
    });
    find = {id: win.id, parent: parent.id, keep};
}

async function hide() {
    if (!find)
        return;
    if (find.keep) {
        await browser.windows.update(find.id, {state: "minimized"});
        if (find.parent)
            browser.windows.update(find.parent, {focused: true}).catch(() => {});
    } else {
        const id = find.id;
        find = null;
        await browser.windows.remove(id).catch(() => {});
    }
}

// um pedido de cada vez (dois cliques seguidos não abrem duas janelas)
function serial(fn) {
    return (...args) => {
        opening = (opening || Promise.resolve()).then(() => fn(...args)).catch(e => console.error("Localizar:", e));
        return opening;
    };
}

// o botão Procurar abre e fecha
browser.browserAction.onClicked.addListener(serial(async tab => {
    if (await visible())
        await hide();
    else
        await show(await parentOf(tab));
}));

// Ctrl+F abre, ou traz para a frente a que já está aberta
browser.commands.onCommand.addListener(serial(async (command, tab) => {
    if (command !== "localizar")
        return;
    if (await visible() && tab && tab.windowId === find.id) {
        browser.runtime.sendMessage({op: "shown"}).catch(() => {});
        return;
    }
    await show(await parentOf(tab));
}));

// a página Localizar pergunta onde procurar, e pede para se esconder
browser.runtime.onMessage.addListener(msg => {
    if (msg.op === "parent")
        return Promise.resolve(find ? find.parent : null);
    if (msg.op === "hide")
        return serial(hide)();
});

browser.windows.onRemoved.addListener(async id => {
    if (!find)
        return;
    if (id === find.id) {
        find = null;
        return;
    }
    // (sem janelas normais, a janela pronta não pode prender o browser aberto)
    const normal = await browser.windows.getAll({windowTypes: ["normal"]});
    if (!normal.length) {
        const fid = find.id;
        find = null;
        browser.windows.remove(fid).catch(() => {});
    } else if (id === find.parent) {
        // (como no IE: a janela Localizar vai-se com a sua janela)
        find.parent = null;
        serial(hide)();
    }
});
