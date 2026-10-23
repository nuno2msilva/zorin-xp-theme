/*
 * Zorin XP — zorin-taskbar settings as a Windows XP property sheet: title
 * and close button on the blue bar, tabs in the window's body, aligned to
 * the left (Gtk.Notebook, which the theme draws as XP's tabs), and not on
 * the title bar where AdwPreferencesWindow puts them.
 *
 * The installer copies the system's zorin-taskbar to the home folder (it
 * takes priority over the system one), renames the original prefs.js to
 * prefs-zorin.js — without changing it — and adds this file, which only
 * rearranges the window after Zorin's code has filled it.
 */
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';

import ZorinTaskbarPreferences from './prefs-zorin.js';

// margins of the tab in the window's body, measured on an XP property
// sheet: 7 px at the top (to the selected one), 5 on the left, 6 on the
// right (after the frame's shadow); 9 px to the OK/Cancel/Apply buttons,
// which sit 6 px from each other and from the right and 8 px from the bottom
const MARGIN = {top: 7, start: 5, end: 6, bottom: 9};
const BUTTONS_MARGIN = {end: 6, bottom: 8, spacing: 6};
// property sheet taller than wide, like XP's
const SIZE = [495, 600];

// scrollbar arrow step and repetition while holding them pressed
// (the same timings as the Start menu)
const SCROLL_STEP = 24;
const REPEAT_DELAY = 330, REPEAT_INTERVAL = 50;

const GEAR = 'emblem-system-symbolic';
// Zorin writes the sliders' value 500 ms after they move
const SCALE_SETTLE_MS = 600;

// texts of XP's dialogs (Zorin's extension does not have them)
const TEXTS = {
    pt: {settings: 'Definições', ok: 'OK', cancel: 'Cancelar', apply: 'Aplicar', title: 'Propriedades da barra de tarefas'},
    es: {settings: 'Configuración', ok: 'Aceptar', cancel: 'Cancelar', apply: 'Aplicar', title: 'Propiedades de la barra de tareas'},
    fr: {settings: 'Paramètres', ok: 'OK', cancel: 'Annuler', apply: 'Appliquer', title: 'Propriétés de la Barre des tâches'},
    de: {settings: 'Einstellungen', ok: 'OK', cancel: 'Abbrechen', apply: 'Übernehmen', title: 'Eigenschaften von Taskleiste'},
    en: {settings: 'Settings', ok: 'OK', cancel: 'Cancel', apply: 'Apply', title: 'Taskbar Properties'},
};
// shorter names in the panel elements list (Position tab)
const SHORT_NAMES = {
    pt: {'Menu do sistema': 'Sistema', 'Menu de data': 'Data', 'Botão do ambiente de trabalho': 'Ver ADT'},
};
const LANG = GLib.get_language_names().map(l => l.slice(0, 2)).find(l => l in TEXTS) ?? 'en';
const T = TEXTS[LANG];

function* descendants(widget) {
    for (let c = widget.get_first_child(); c; c = c.get_next_sibling()) {
        yield c;
        yield* descendants(c);
    }
}

// buttons with the gear → a "Definições" (Settings) button, the most common in XP
function xpGearButton(button) {
    const child = button.get_child();
    if (button.get_icon_name() !== GEAR && !(child instanceof Gtk.Image && child.get_icon_name() === GEAR)) {
        // icon-only buttons (arrows of the elements list): without the 75 px
        // minimum width of text buttons
        if (child instanceof Gtk.Image) {
            button.add_css_class('image-button');
            // ↑ ↓: only XP's blue arrow, without a button underneath
            const dir = {'go-up-symbolic': 'up', 'go-down-symbolic': 'down'}[child.get_icon_name()];
            if (dir) {
                button.add_css_class('zxp-arrow');
                button.add_css_class(dir);
                // (the grid of the two arrows does not share the row's height:
                // it centres itself)
                button.get_parent().valign = Gtk.Align.CENTER;
                child.visible = false;
            }
        }
        return;
    }
    button.set_label(T.settings);
    button.remove_css_class('circular');
    button.remove_css_class('image-button');
}

function xpGearButtons(root) {
    if (root instanceof Gtk.Button)
        xpGearButton(root);
    for (const w of descendants(root)) {
        if (w instanceof Gtk.Button)
            xpGearButton(w);
        // names of the panel elements: shorter and on several lines if needed
        if (w instanceof Gtk.Label && w.get_parent() instanceof Gtk.Grid) {
            w.wrap = true;
            const short = SHORT_NAMES[LANG]?.[w.label];
            if (short) {
                w.tooltip_text = w.label;
                w.label = short;
            }
        }
        if (w instanceof Gtk.ToggleButton && w.get_parent() instanceof Gtk.Grid)
            xpVisibleCheck(w);
    }
}

// each element's "Visível" button → a check box, which takes less space.
// The button leaves the grid but stays alive and connected to the box: it is
// from it that Zorin reads the state (row.visibleToggleBtn) and gets the
// toggled signal.
function xpVisibleCheck(toggle) {
    const grid = toggle.get_parent();
    const [col, row] = grid.query_child(toggle);
    const check = new Gtk.CheckButton({tooltip_text: toggle.label, valign: Gtk.Align.CENTER});
    toggle.bind_property('active', check, 'active',
        GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE);
    grid.remove(toggle);
    grid.attach(check, col, row, 1, 1);
}

// rows with a slider (or with a row of buttons): the controls move to a row
// of their own, below the title, full width, like the control bars of XP's
// dialogs — and the window can be narrow like XP's
function xpSliderRow(row) {
    const header = row.get_first_child();
    const suffixes = [...descendants(header)].find(w => w.has_css_class('suffixes'));
    if (!suffixes)
        return;
    const controls = [...descendants(suffixes)];
    const scales = controls.filter(w => w instanceof Gtk.Scale);
    if (!scales.length && controls.filter(w => w instanceof Gtk.Button).length < 3)
        return;
    scales.forEach(sc => {
        sc.hexpand = true;
        sc.width_request = -1;
    });
    header.orientation = Gtk.Orientation.VERTICAL;
    header.add_css_class('zxp-slider-row');
    suffixes.halign = Gtk.Align.FILL;
    suffixes.hexpand = true;
    // check boxes that go with the slider ("Dinâmico") sit below it
    const checks = controls.filter(w => w instanceof Gtk.CheckButton && w.get_parent() === suffixes);
    if (scales.length && checks.length) {
        suffixes.orientation = Gtk.Orientation.VERTICAL;
        for (const c of checks) {
            if (c !== suffixes.get_last_child())
                suffixes.reorder_child_after(c, suffixes.get_last_child());
            c.halign = Gtk.Align.START;
        }
    }
}

// group of option (radio) buttons for choices Zorin shows as toggle
// buttons or a drop-down list
function radioBox(row, orientation = Gtk.Orientation.HORIZONTAL) {
    const box = new Gtk.Box({orientation, spacing: 14, css_classes: ['zxp-radios'], valign: Gtk.Align.CENTER});
    row.add_suffix(box);
    return box;
}

// "Posição do painel": Abaixo/Acima/Esquerda/Direita as option buttons.
// Zorin's toggle buttons leave the row but they are still what changes the
// setting (the clicked signal) and reflects the state (set_active).
function xpPositionRadios(builder) {
    const ids = ['bottom', 'top', 'left', 'right'].map(p => `position_${p}_button`);
    const toggles = ids.map(id => builder.get_object(id));
    if (toggles.some(t => !t))
        return;
    const row = toggles[0].get_ancestor(Adw.ActionRow);
    // the four options in a row of their own, below the title
    const header = row.get_first_child();
    header.orientation = Gtk.Orientation.VERTICAL;
    header.add_css_class('zxp-slider-row');
    const box = radioBox(row);
    let group = null;
    for (const toggle of toggles) {
        const radio = new Gtk.CheckButton({label: toggle.label, group, active: toggle.active});
        group ??= radio;
        toggle.connect('notify::active', () => {
            if (toggle.active)
                radio.active = true;
        });
        radio.connect('toggled', () => {
            if (radio.active && !toggle.active)
                toggle.activate();
        });
        row.remove(toggle);
        box.append(radio);
    }
}

// "Âncora": Início/Centro/Fim as option buttons instead of the drop-down
// list. Zorin changes the texts depending on whether the panel is
// horizontal or vertical (remove_all/append), so the buttons follow the
// list's model.
function xpAnchorRadios(builder) {
    const combo = builder.get_object('panel_anchor_combo');
    if (!combo)
        return;
    const row = combo.get_ancestor(Adw.ActionRow);
    const box = radioBox(row);
    const radios = new Map();
    let syncing = false;
    const sync = () => {
        syncing = true;
        const model = combo.get_model();
        const seen = new Set();
        for (let i = 0; i < model.iter_n_children(null); i++) {
            const [, iter] = model.iter_nth_child(null, i);
            const label = model.get_value(iter, 0), id = model.get_value(iter, 1);
            let radio = radios.get(id);
            if (!radio) {
                // (the group is only set once: putting it in the same group again sends
                // GTK into an infinite loop)
                radio = new Gtk.CheckButton({group: radios.values().next().value ?? null});
                radio.connect('toggled', () => {
                    if (!syncing && radio.active && combo.get_active_id() !== id)
                        combo.set_active_id(id);
                });
                radios.set(id, radio);
                box.append(radio);
            }
            radio.label = label;
            radio.visible = true;
            seen.add(id);
        }
        for (const [id, radio] of radios) {
            if (!seen.has(id))
                radio.visible = false;
        }
        radios.get(combo.get_active_id())?.set_active(true);
        syncing = false;
    };
    combo.connect('changed', sync);
    combo.get_model().connect('row-inserted', () => GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
        sync();
        return GLib.SOURCE_REMOVE;
    }));
    combo.bind_property('sensitive', box, 'sensitive', GObject.BindingFlags.SYNC_CREATE);
    sync();
    row.remove(combo);
}

// XP vertical scrollbar, with arrows: GTK4 no longer has arrows on its
// scrollbars, so the page's one is hidden (EXTERNAL) and built here — arrow,
// bar, arrow — on the same adjustment. As in the Start menu, it only
// scrolls on click: one step on press, repeating after 330 ms while pressed.
function xpScrolledPage(page) {
    const sw = page.get_first_child();
    if (!(sw instanceof Gtk.ScrolledWindow))
        return page;
    sw.vscrollbar_policy = Gtk.PolicyType.EXTERNAL;
    const adj = sw.get_vadjustment();

    const arrow = (cls, dir) => {
        const btn = new Gtk.Button({css_classes: ['zxp-scroll-arrow', cls], focusable: false});
        const click = new Gtk.GestureClick({propagation_phase: Gtk.PropagationPhase.CAPTURE});
        let timer = 0;
        const stop = () => {
            if (timer)
                GLib.source_remove(timer);
            timer = 0;
            btn.unset_state_flags(Gtk.StateFlags.ACTIVE);
        };
        const step = () => {
            adj.value = Math.max(adj.lower, Math.min(adj.upper - adj.page_size, adj.value + dir * SCROLL_STEP));
        };
        click.connect('pressed', () => {
            click.set_state(Gtk.EventSequenceState.CLAIMED);
            stop();
            btn.set_state_flags(Gtk.StateFlags.ACTIVE, false);
            step();
            timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, REPEAT_DELAY, () => {
                timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, REPEAT_INTERVAL, () => {
                    step();
                    return GLib.SOURCE_CONTINUE;
                });
                return GLib.SOURCE_REMOVE;
            });
        });
        click.connect('released', stop);
        click.connect('cancel', stop);
        click.connect('stopped', stop);
        btn.add_controller(click);
        btn.connect('destroy', stop);
        return btn;
    };

    const up = arrow('up', -1), down = arrow('down', 1);
    const bar = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL, css_classes: ['zxp-vscroll']});
    bar.append(up);
    bar.append(new Gtk.Scrollbar({orientation: Gtk.Orientation.VERTICAL, adjustment: adj, vexpand: true}));
    bar.append(down);

    const sync = () => {
        bar.visible = adj.upper - adj.page_size > 0.5;
        up.sensitive = adj.value > adj.lower;
        down.sensitive = adj.value < adj.upper - adj.page_size - 0.5;
    };
    adj.connect('changed', sync);
    adj.connect('value-changed', sync);
    sync();

    const box = new Gtk.Box();
    page.hexpand = true;
    box.append(page);
    box.append(bar);
    return box;
}

// AdwPreferencesGroup → XP group box, with the title embedded in the
// outline and the line interrupted behind it. GTK4's Gtk.Frame no longer
// opens that gap, so the box is built from pieces the theme draws:
//   ╭─ Title ──────────╮   .zxp-gb-tl  label.zxp-gb-title  .zxp-gb-tr
//   │ list …           │   .zxp-gb-body (sides and bottom)
//   ╰──────────────────╯
function xpGroupBox(group) {
    const inner = group.get_first_child();
    const header = inner?.get_first_child();
    const content = header?.get_next_sibling();
    if (!content || content.get_parent() !== inner)
        return;
    const title = group.get_title();
    const box = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL, css_classes: ['zxp-groupbox']});
    if (title) {
        const top = new Gtk.Box();
        top.append(new Gtk.Box({css_classes: ['zxp-gb-tl']}));
        const label = new Gtk.Label({label: title, css_classes: ['zxp-gb-title']});
        group.bind_property('title', label, 'label', GObject.BindingFlags.DEFAULT);
        top.append(label);
        top.append(new Gtk.Box({css_classes: ['zxp-gb-tr'], hexpand: true}));
        box.append(top);
    } else {
        box.add_css_class('untitled');
    }
    header.visible = false;
    inner.remove(content);
    content.add_css_class('zxp-gb-body');
    box.append(content);
    inner.append(box);
}

export default class ZorinTaskbarXpPreferences extends ZorinTaskbarPreferences {
    fillPreferencesWindow(window) {
        // the pages Zorin's code adds (Style, Position, …)
        const pages = [];
        const add = window.add;
        window.add = function (page) {
            pages.push(page);
            return add.call(this, page);
        };
        // and the Gtk.Builder where Zorin loads the .ui files (pages and option windows)
        const builders = [];
        const setScope = Gtk.Builder.prototype.set_scope;
        Gtk.Builder.prototype.set_scope = function (...args) {
            builders.push(this);
            return setScope.apply(this, args);
        };
        try {
            super.fillPreferencesWindow(window);
        } finally {
            delete window.add;
            Gtk.Builder.prototype.set_scope = setScope;
        }
        if (!pages.length)
            return;

        // every group, also the option windows' ones (they come from the same Gtk.Builder)
        const objects = builders.flatMap(b => b.get_objects());
        objects.filter(o => o instanceof Adw.PreferencesGroup).forEach(xpGroupBox);
        // (rows without an id do not come in get_objects: walk the tree)
        if (builders[0]) {
            xpPositionRadios(builders[0]);
            xpAnchorRadios(builders[0]);
        }
        const widgets = new Set(objects.filter(o => o instanceof Gtk.Widget)
            .flatMap(o => [o, ...descendants(o)]));
        [...widgets].filter(w => w instanceof Adw.ActionRow).forEach(xpSliderRow);
        objects.filter(o => o instanceof Gtk.Button).forEach(xpGearButton);
        // the panel elements list (Position) is rebuilt by Zorin
        for (const list of objects.filter(o => o instanceof Gtk.ListBox)) {
            xpGearButtons(list);
            list.observe_children().connect('items-changed', () => xpGearButtons(list));
        }

        const notebook = new Gtk.Notebook({
            margin_top: MARGIN.top,
            margin_bottom: MARGIN.bottom,
            margin_start: MARGIN.start,
            margin_end: MARGIN.end,
            scrollable: false,
        });
        for (const page of pages) {
            // the page takes the tab's width (AdwClamp limits it to 600 px)
            for (let c = page.get_first_child(); c; c = c.get_first_child()) {
                if (c instanceof Adw.Clamp) {
                    c.maximum_size = c.tightening_threshold = 10000;
                    break;
                }
            }
            window.remove(page);
            notebook.append_page(xpScrolledPage(page), new Gtk.Label({label: page.get_title()}));
        }
        // the extensions dialog requires a page in the original structure (which
        // is no longer visible): an empty one avoids the "did not provide any UI" error
        window.add(new Adw.PreferencesPage());

        // title on the left, as in XP's dialogs (AdwHeaderBar centres it)
        const title = new Gtk.Label({label: window.get_title() ?? '', css_classes: ['title'], xalign: 0});
        window.bind_property('title', title, 'label', GObject.BindingFlags.SYNC_CREATE);
        const header = new Adw.HeaderBar({title_widget: new Adw.Bin()});
        header.pack_start(title);
        const content = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL});
        notebook.vexpand = true;
        content.append(notebook);
        content.append(this._xpButtons(window));
        const view = new Adw.ToolbarView({content});
        view.add_top_bar(header);
        window.set_content(view);
        window.add_css_class('zxp-property-sheet');
        // XP-style title ("Propriedades da barra de tarefas")
        window.set_title(T.title);
        window.set_default_size(...SIZE);

        // "go to page X" (target-prefs-page) now picks the tab
        window.set_visible_page_name = name => {
            const i = pages.findIndex(p => p.get_name() === name);
            if (i >= 0)
                notebook.set_current_page(i);
        };
    }

    // OK / Cancel / Apply, as on XP's property sheets. The settings go into
    // delayed mode (Gio.Settings.delay): the controls stay bound to them, but
    // nothing reaches the panel until Apply or OK; Cancel and the close
    // button discard what was not applied.
    _xpButtons(window) {
        const settings = [window._settings, window._gnomeInterfaceSettings].filter(s => s);
        settings.forEach(s => s.delay());
        // Zorin writes the same values again when filling the window, so
        // has-unapplied is not enough: compare with what is stored
        const saved = settings.map(s => new Gio.Settings({settings_schema: s.settings_schema, path: s.path}));
        const pending = () => settings.some((s, i) => s.settings_schema.list_keys()
            .some(k => !s.get_value(k).equal(saved[i].get_value(k))));
        const apply = () => settings.forEach(s => s.apply());
        const revert = () => settings.forEach(s => s.revert());

        const box = new Gtk.Box({
            halign: Gtk.Align.END,
            spacing: BUTTONS_MARGIN.spacing,
            margin_end: BUTTONS_MARGIN.end,
            margin_bottom: BUTTONS_MARGIN.bottom,
            css_classes: ['zxp-dialog-buttons'],
        });
        const ok = new Gtk.Button({label: T.ok, css_classes: ['default']});
        const cancel = new Gtk.Button({label: T.cancel});
        const applyBtn = new Gtk.Button({label: T.apply, sensitive: false});
        [ok, cancel, applyBtn].forEach(b => box.append(b));

        // Zorin's sliders only write 500 ms after being released: OK hides the
        // window at once and applies/closes after that; Apply repeats

        const afterScales = fn => GLib.timeout_add(GLib.PRIORITY_DEFAULT, SCALE_SETTLE_MS, () => {
            fn();
            return GLib.SOURCE_REMOVE;
        });
        ok.connect('clicked', () => {
            window.set_visible(false);
            afterScales(() => {
                apply();
                window.close();
            });
        });
        cancel.connect('clicked', () => window.close());
        applyBtn.connect('clicked', () => {
            apply();
            afterScales(apply);
        });
        const sync = () => (applyBtn.sensitive = pending());
        [...settings, ...saved].forEach(s => s.connect('changed', sync));
        settings.forEach(s => s.connect('notify::has-unapplied', sync));
        window.connect('close-request', () => {
            revert();
            return false;
        });
        window.set_default_widget(ok);
        return box;
    }
}
