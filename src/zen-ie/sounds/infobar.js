// The sounds of IE6 SP2's information bar, from the page (it only listens:
// the page does what it always does). There are no events for extensions to
// know when the browser blocks a window or asks for a permission, so:
//   - pop-up blocked: the page's window.open returned null;
//   - permission request: the page asked for the location, notifications,
//     camera or microphone and the answer is still "ask".
const page = window.wrappedJSObject;
const tell = op => browser.runtime.sendMessage({op}).catch(() => {});

function wrap(target, name, before, after) {
    const original = target[name];
    if (typeof original !== "function")
        return;
    exportFunction(function (...args) {
        before?.call(this);
        // (one by one: the page's function cannot read an array from this side)
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
