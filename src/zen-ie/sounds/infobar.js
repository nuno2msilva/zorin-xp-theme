// Os sons da barra de informações do IE6 SP2, a partir da página (só ouve: a
// página faz o mesmo de sempre). Não há eventos para as extensões saberem
// quando o browser bloqueia uma janela ou pede uma permissão, por isso:
//   - pop-up bloqueado: o window.open da página devolveu null;
//   - pedido de permissão: a página pediu a localização, as notificações, a
//     câmara ou o microfone e a resposta ainda é "perguntar".
const page = window.wrappedJSObject;
const tell = op => browser.runtime.sendMessage({op}).catch(() => {});

function wrap(target, name, before, after) {
    const original = target[name];
    if (typeof original !== "function")
        return;
    exportFunction(function (...args) {
        before?.call(this);
        // (um a um: a função da página não pode ler um array deste lado)
        const result = original.call(this, ...args);
        after?.(result);
        return result;
    }, target, {defineAs: name});
}

async function asking(name) {
    try {
        return (await navigator.permissions.query({name})).state === "prompt";
    } catch {
        return false;
    }
}

wrap(page, "open", null, w => {
    if (w === null)
        tell("popup-blocked");
});
if (page.Geolocation) {
    for (const name of ["getCurrentPosition", "watchPosition"])
        wrap(page.Geolocation.prototype, name, () => asking("geolocation").then(p => p && tell("infobar")));
}
if (page.Notification) {
    wrap(page.Notification, "requestPermission", () => {
        if (Notification.permission === "default")
            tell("infobar");
    });
}
if (page.MediaDevices) {
    wrap(page.MediaDevices.prototype, "getUserMedia", () => {
        Promise.all([asking("camera"), asking("microphone")]).then(p => p.some(Boolean) && tell("infobar"));
    });
}
