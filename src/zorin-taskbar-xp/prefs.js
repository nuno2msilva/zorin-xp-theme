/*
 * Zorin XP — definições da zorin-taskbar como uma folha de propriedades do
 * Windows XP: título e botão de fechar na barra azul, separadores no corpo da
 * janela, alinhados à esquerda (Gtk.Notebook, que o tema desenha como os
 * separadores do XP), e não na barra de título como o AdwPreferencesWindow
 * os põe.
 *
 * O instalador copia a zorin-taskbar do sistema para a pasta pessoal (tem
 * prioridade sobre a do sistema), muda o nome do prefs.js original para
 * prefs-zorin.js — sem o alterar — e acrescenta este ficheiro, que só
 * reorganiza a janela depois de o código da Zorin a preencher.
 */
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';

import ZorinTaskbarPreferences from './prefs-zorin.js';

// margens do separador no corpo da janela, medidas numa folha de propriedades
// do XP: 7 px em cima (até ao selecionado), 5 à esquerda, 6 à direita (depois
// da sombra da moldura); 9 px até aos botões OK/Cancelar/Aplicar, que ficam
// a 6 px uns dos outros e da direita e a 8 px do fundo
const MARGIN = {top: 7, start: 5, end: 6, bottom: 9};
const BUTTONS_MARGIN = {end: 6, bottom: 8, spacing: 6};
// folha de propriedades mais alta do que larga, como as do XP
const SIZE = [495, 600];

// passo das setas da barra de deslocamento e repetição ao mantê-las premidas
// (os mesmos tempos do menu Iniciar)
const SCROLL_STEP = 24;
const REPEAT_DELAY = 330, REPEAT_INTERVAL = 50;

const GEAR = 'emblem-system-symbolic';
// a Zorin escreve o valor dos deslizadores 500 ms depois de mexidos
const SCALE_SETTLE_MS = 600;

// textos dos diálogos do XP (a extensão da Zorin não os tem)
const TEXTS = {
    pt: {settings: 'Definições', ok: 'OK', cancel: 'Cancelar', apply: 'Aplicar', title: 'Propriedades da barra de tarefas'},
    es: {settings: 'Configuración', ok: 'Aceptar', cancel: 'Cancelar', apply: 'Aplicar', title: 'Propiedades de la barra de tareas'},
    fr: {settings: 'Paramètres', ok: 'OK', cancel: 'Annuler', apply: 'Appliquer', title: 'Propriétés de la Barre des tâches'},
    de: {settings: 'Einstellungen', ok: 'OK', cancel: 'Abbrechen', apply: 'Übernehmen', title: 'Eigenschaften von Taskleiste'},
    en: {settings: 'Settings', ok: 'OK', cancel: 'Cancel', apply: 'Apply', title: 'Taskbar Properties'},
};
// nomes mais curtos na lista de elementos do painel (separador Posição)
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

// botões com a engrenagem → botão "Definições", o mais comum no XP
function xpGearButton(button) {
    const child = button.get_child();
    if (button.get_icon_name() !== GEAR && !(child instanceof Gtk.Image && child.get_icon_name() === GEAR)) {
        // botões só com ícone (setas da lista de elementos): sem a largura
        // mínima de 75 px dos botões de texto
        if (child instanceof Gtk.Image) {
            button.add_css_class('image-button');
            // ↑ ↓: só a seta azul do XP, sem botão por baixo
            const dir = {'go-up-symbolic': 'up', 'go-down-symbolic': 'down'}[child.get_icon_name()];
            if (dir) {
                button.add_css_class('zxp-arrow');
                button.add_css_class(dir);
                // (a grelha das duas setas não reparte a altura da linha:
                // centra-se ela própria)
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
        // nomes dos elementos do painel: mais curtos e em várias linhas se
        // for preciso
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

// o botão "Visível" de cada elemento → caixa de verificação, que ocupa menos.
// O botão sai da grelha mas continua vivo e ligado à caixa: é dele que a
// Zorin lê o estado (row.visibleToggleBtn) e recebe o sinal toggled.
function xpVisibleCheck(toggle) {
    const grid = toggle.get_parent();
    const [col, row] = grid.query_child(toggle);
    const check = new Gtk.CheckButton({tooltip_text: toggle.label, valign: Gtk.Align.CENTER});
    toggle.bind_property('active', check, 'active',
        GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE);
    grid.remove(toggle);
    grid.attach(check, col, row, 1, 1);
}

// linhas com deslizador (ou com uma fila de botões): os controlos passam para
// uma linha própria, por baixo do título, a toda a largura, como as barras de
// controlo dos diálogos do XP — e a janela pode ser estreita como as do XP
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
    // caixas de verificação que acompanham o deslizador ("Dinâmico") ficam
    // por baixo dele
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

// grupo de botões de opção (rádio) para escolhas que a Zorin mostra como
// botões de alternar ou lista pendente
function radioBox(row, orientation = Gtk.Orientation.HORIZONTAL) {
    const box = new Gtk.Box({orientation, spacing: 14, css_classes: ['zxp-radios'], valign: Gtk.Align.CENTER});
    row.add_suffix(box);
    return box;
}

// "Posição do painel": Abaixo/Acima/Esquerda/Direita em botões de opção. Os
// botões de alternar da Zorin saem da linha mas continuam a ser eles a mudar
// a definição (o sinal clicked) e a refletir o estado (set_active).
function xpPositionRadios(builder) {
    const ids = ['bottom', 'top', 'left', 'right'].map(p => `position_${p}_button`);
    const toggles = ids.map(id => builder.get_object(id));
    if (toggles.some(t => !t))
        return;
    const row = toggles[0].get_ancestor(Adw.ActionRow);
    // as quatro opções numa linha própria, por baixo do título
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

// "Âncora": Início/Centro/Fim em botões de opção em vez da lista pendente. A
// Zorin muda os textos conforme o painel é horizontal ou vertical
// (remove_all/append), por isso os botões seguem o modelo da lista.
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
                // (o grupo só se define uma vez: voltar a pô-lo no mesmo
                // grupo deixa o GTK em ciclo infinito)
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

// barra de deslocamento vertical do XP, com setas: o GTK4 já não tem setas
// nas barras, por isso a da página é escondida (EXTERNAL) e montada aqui —
// seta, barra, seta — sobre o mesmo ajuste. Como no menu Iniciar, só desloca
// ao clicar: um passo ao premir, e repete após 330 ms enquanto premida.
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

// AdwPreferencesGroup → caixa de grupo do XP, com o título embutido no
// contorno e o traço interrompido atrás dele. O Gtk.Frame do GTK4 já não abre
// esse intervalo, por isso a caixa é montada em peças que o tema desenha:
//   ╭─ Título ─────────╮   .zxp-gb-tl  label.zxp-gb-title  .zxp-gb-tr
//   │ lista …          │   .zxp-gb-body (lados e fundo)
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
        // as páginas que o código da Zorin acrescenta (Estilo, Posição, …)
        const pages = [];
        const add = window.add;
        window.add = function (page) {
            pages.push(page);
            return add.call(this, page);
        };
        // e o Gtk.Builder onde a Zorin carrega os .ui (páginas e janelas de opções)
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

        // todos os grupos, também os das janelas de opções (vêm do mesmo Gtk.Builder)
        const objects = builders.flatMap(b => b.get_objects());
        objects.filter(o => o instanceof Adw.PreferencesGroup).forEach(xpGroupBox);
        // (as linhas sem id não vêm em get_objects: percorre-se a árvore)
        if (builders[0]) {
            xpPositionRadios(builders[0]);
            xpAnchorRadios(builders[0]);
        }
        const widgets = new Set(objects.filter(o => o instanceof Gtk.Widget)
            .flatMap(o => [o, ...descendants(o)]));
        [...widgets].filter(w => w instanceof Adw.ActionRow).forEach(xpSliderRow);
        objects.filter(o => o instanceof Gtk.Button).forEach(xpGearButton);
        // a lista dos elementos do painel (Posição) é refeita pela Zorin
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
            // a página ocupa a largura do separador (o AdwClamp limita-a a 600 px)
            for (let c = page.get_first_child(); c; c = c.get_first_child()) {
                if (c instanceof Adw.Clamp) {
                    c.maximum_size = c.tightening_threshold = 10000;
                    break;
                }
            }
            window.remove(page);
            notebook.append_page(xpScrolledPage(page), new Gtk.Label({label: page.get_title()}));
        }
        // o diálogo das extensões exige uma página na estrutura original (que
        // deixa de se ver): uma vazia evita o erro "did not provide any UI"
        window.add(new Adw.PreferencesPage());

        // título à esquerda, como nos diálogos do XP (o AdwHeaderBar centra-o)
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
        // título à maneira do XP ("Propriedades da barra de tarefas")
        window.set_title(T.title);
        window.set_default_size(...SIZE);

        // "ir para a página X" (target-prefs-page) passa a escolher o separador
        window.set_visible_page_name = name => {
            const i = pages.findIndex(p => p.get_name() === name);
            if (i >= 0)
                notebook.set_current_page(i);
        };
    }

    // OK / Cancelar / Aplicar, como nas folhas de propriedades do XP. As
    // definições passam a modo diferido (Gio.Settings.delay): os controlos
    // continuam ligados a elas, mas nada chega ao painel até Aplicar ou OK;
    // Cancelar e o botão de fechar descartam o que não foi aplicado.
    _xpButtons(window) {
        const settings = [window._settings, window._gnomeInterfaceSettings].filter(s => s);
        settings.forEach(s => s.delay());
        // a Zorin volta a escrever valores iguais ao preencher a janela, por
        // isso has-unapplied não chega: compara-se com o que está gravado
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

        // os deslizadores da Zorin só escrevem 500 ms depois de largados: OK
        // esconde logo a janela e aplica/fecha depois disso; Aplicar repete
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
