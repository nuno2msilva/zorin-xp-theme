/*
 * The Preferences page (about:addons > Preferências): each box turns a
 * feature on or off at once (experiments/settings), and follows changes made
 * elsewhere (another open copy of the page).
 */
const boxes = [...document.querySelectorAll("input[data-feature]")];

browser.zxpSettings.get().then(all => {
    for (const box of boxes)
        box.checked = all[box.dataset.feature] !== false;
});

for (const box of boxes)
    box.addEventListener("change", () => browser.zxpSettings.set(box.dataset.feature, box.checked));

browser.zxpSettings.onChanged.addListener((name, value) => {
    const box = boxes.find(b => b.dataset.feature === name);
    if (box)
        box.checked = value;
});
