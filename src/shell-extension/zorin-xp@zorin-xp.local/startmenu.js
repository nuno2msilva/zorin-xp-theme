/*
 * Menu Iniciar do Zorin com o aspeto do menu Iniciar do Windows XP.
 *
 * Mantém o conteúdo e o comportamento do zorin-menu (disposição "ALL":
 * categorias + pesquisa à esquerda, locais e atalhos à direita) e
 * reorganiza-o como o XP (medidas de capturas reais, menu de 380 px):
 *   ┌ faixa StartUserPanel (64 px): fotografia 48 px em (9,9) com a moldura
 *   │ UserTileBackground em (1,1), nome em Franklin Gothic Medium 14 pt em x 67
 *   ├ coluna esquerda 190 px (ProgList) │ coluna direita 190 px (PlacesList)
 *   └ faixa StartPanelLogoff (41 px): pesquisa oculta (escrever para pesquisar); "Terminar sessão" e
 *     "Encerrar" à mesma distância da direita que no XP (x 185 e 302 em 380)
 * O utilizador da coluna direita passa para a faixa de cima; os botões de
 * sessão do Zorin dão lugar aos do XP; a pesquisa vai para a faixa de baixo.
 * Ícones, categorias e "Todos os Programas" ficam como no Zorin.
 */
import AccountsService from 'gi://AccountsService';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

import {XP_DIR, slicedImage} from './images.js';
import {showEndSession, LOGOUT, SHUTDOWN} from './endSession.js';

const MENU_UUID = 'zorin-menu@zorinos.com';

// fecha o menu Iniciar (todos os monitores) de imediato, sem animação
export function closeStartMenus() {
    const buttons = Main.extensionManager.lookup(MENU_UUID)?.stateObj?.menuButtons ?? [];
    for (const b of buttons) {
        if (b?._menu?.isOpen)
            b._menu.close(BoxPointer.PopupAnimation.NONE);
    }
}
const HEADER_H = 64;
const FOOTER_H = 41;
// Larguras iguais às de tools/builders/shelltheme.py (o XP tinha 380 = 190 + 190)
const START_W = 380, LEFT_W = 190, RIGHT_W = START_W - LEFT_W;
// Botões da faixa de baixo como no XP: ícones em x=184 e 301 (em 380)
const LOGOFF_X = START_W - 196, SHUTDOWN_X = START_W - 79;
const SEARCH_X = 8, SEARCH_W = 150, SEARCH_H = 20;
const SEP_H = 9;  // separadores do XP: 9 px com a linha de 2 px
// Coluna esquerda (medidas de capturas do XP, a contar do topo da faixa de
// baixo F): linha do separador em F-36, "Todos os programas" (seta 16×24 e
// destaque) de F-29 a F-6, 5 px de margem por baixo (ProgList ContentMargins)
const LEFT_PAD_T = 6, LEFT_PAD_B = 5;
const LEFT_SEP_H = 10;  // separador por cima de "Todos os programas": 3 + linha 2 + 5
const SHADOW_W = 5;     // sombra do XP: 5 px à direita e em baixo
const ARROW_H = 17;     // setas da barra de deslocamento do XP (17×17)

// Diagnóstico: existe ~/.cache/zorin-xp-debug -> registo no diário (journalctl)
const debug = msg => {
    if (GLib.file_test(`${GLib.get_user_cache_dir()}/zorin-xp-debug`, GLib.FileTest.EXISTS))
        console.log(`ZXP ${msg}`);
};

export class StartMenuTweaks {
    constructor(ext) {
        this._ext = ext;
        this._patches = [];
        this._load().catch(e => console.error(`Zorin XP: menu Iniciar: ${e}`));
    }

    async _load() {
        const menu = Main.extensionManager.lookup(MENU_UUID);
        if (!menu)
            return;
        const mod = await import(`file://${menu.path}/layouts/standardLayout.js`);
        this._misc = await import(`file://${menu.path}/widgets/miscMenuItems.js`);
        const base = await import(`file://${menu.path}/widgets/baseMenuItem.js`);
        if (this._destroyed)
            return;
        const proto = mod.StandardLayout.prototype;
        const self = this;

        this._patch(proto, '_loadLayout', function (orig) {
            orig.call(this);
            try {
                self._xpify(this);
            } catch (e) {
                console.error(`Zorin XP: menu Iniciar: ${e}\n${e.stack}`);
            }
        });
        // Nada pré-selecionado: o Zorin dá o foco do teclado ao primeiro item
        // ao abrir o menu (e ao primeiro programa ao abrir uma categoria), o
        // que o realça e faz a lista saltar para ele. Como no XP, o foco fica
        // no próprio menu até se usar o teclado: a primeira seta seleciona o
        // primeiro item (BaseLayout._onKeyPress) e escrever inicia a pesquisa.
        // Ao abrir uma categoria com o teclado mantém-se o comportamento do Zorin.
        // O realce segue o rato: ao sair de um item, o foco do teclado que o
        // Zorin lhe deu ao passar o rato volta para o menu. Senão o item fica
        // "alvo": quando um grab termina (p. ex. o das setas da barra) o
        // GNOME devolve-lhe o foco e o Zorin realça-o e desloca a lista até ele
        this._patch(base.BaseMenuItem.prototype, '_onHover', function (orig, ...args) {
            orig.call(this, ...args);
            if (this.hover || !this.has_key_focus())
                return;
            for (let a = this.get_parent(); a; a = a.get_parent()) {
                if (a._zxp) {
                    global.stage.set_key_focus(a);
                    break;
                }
            }
        });
        this._patch(proto, 'reset', function (orig) {
            orig.call(this);
            if (this._zxp)
                global.stage.set_key_focus(this);
        });
        // Com o rato, a lista também não recebe o foco: o Zorin focaria o
        // primeiro programa e a lista deslizaria até ao topo (ao reabrir a
        // mesma categoria, que mantém a posição em que ficou)
        this._patch(proto, '_onSelectCategory', function (orig, ...args) {
            const type = Clutter.get_current_event()?.type();
            const keyboard = type === Clutter.EventType.KEY_PRESS || type === Clutter.EventType.KEY_RELEASE;
            const apps = this._appsSection;
            if (!this._zxp || keyboard || !apps) {
                orig.call(this, ...args);
                return;
            }
            apps.grab_key_focus = () => {};
            try {
                orig.call(this, ...args);
            } finally {
                delete apps.grab_key_focus;
            }
            global.stage.set_key_focus(this);
        });
        this._patch(proto, '_availableHeight', function (orig) {
            const h = orig.call(this);
            return this._zxp ? h - HEADER_H - FOOTER_H : h;
        });
        this._patch(proto, 'updateHeight', function (orig) {
            if (!this._zxp) {
                orig.call(this);
                return;
            }
            // altura calculada de raiz (this.height devolveria a altura da
            // abertura anterior e o menu cresceria a cada abertura)
            const available = this._availableHeight();
            const bodyH = this._sidebar.updateHeight(available);
            // tudo com altura fixa: o corpo não pode encolher/esticar com o
            // conteúdo (senão a faixa de baixo sobe e desce)
            this._zxpBody?.set_height(bodyH);
            this.set_height(bodyH + HEADER_H + FOOTER_H + SHADOW_W);
            // sombra: imagem do tamanho exato do menu + 5 px (ver _xpify)
            const shadow = slicedImage('start-shadow', START_W + SHADOW_W,
                bodyH + HEADER_H + FOOTER_H + SHADOW_W, [15, SHADOW_W, SHADOW_W, 10]);
            this.set_style(`padding: 0 ${SHADOW_W}px ${SHADOW_W}px 0; ` +
                `background-image: url("file://${shadow}"); background-position: 0 0; ` +
                'background-repeat: no-repeat;');
            debug(`updateHeight: disponível=${available} altura=${this.height}`);
            // o conteúdo do popup tem padding do tema Zorin: anulá-lo (inline)
            for (let a = this.get_parent(); a; a = a.get_parent()) {
                if (a.has_style_class_name?.('popup-menu-content') ||
                    a.has_style_class_name?.('popup-menu-section'))
                    a.set_style('padding: 0; margin: 0; spacing: 0; border-width: 0;');
                if (a.has_style_class_name?.('popup-menu-boxpointer')) {
                    // sem seta nem margens (o tema Zorin dá rise 4 px e margin-bottom 1.75em)
                    a.set_style('margin: 0; -arrow-rise: 0; -arrow-base: 0; ' +
                        '-arrow-border-width: 0; -arrow-border-radius: 0; -boxpointer-gap: 0;');
                    self._pinBoxPointer(a, this);
                    break;
                }
            }
        });
        this._reloadMenus();
    }

    // Como no XP: o menu abre encostado à esquerda do ecrã, com a base no topo
    // da barra de tarefas. O cálculo do BoxPointer centra-o no botão e o tema
    // Zorin acrescenta margens; aqui a posição é calculada diretamente, com os
    // desvios internos (faixa de topo à esquerda, faixa de baixo em baixo)
    // medidos depois de cada disposição. Sem translações: a animação de
    // abertura repõe-nas a 0 e o menu saltaria.
    _pinBoxPointer(bp, layout) {
        if (bp._zxpPinned)
            return;
        bp._zxpPinned = true;
        // desvios internos já medidos com o tema Zorin (evitam que a primeira
        // abertura apareça desalinhada por um instante); confirmados a seguir
        bp._zxpOx = 0;   // da esquerda do BoxPointer à esquerda da faixa de topo
        bp._zxpOb = 5;   // da base da faixa de baixo à base do BoxPointer (a sombra)
        bp.translation_x = 0;
        bp.translation_y = 0;
        bp._reposition = function (box) {
            const src = this._sourceActor;
            const monitor = Main.layoutManager.findIndexForActor(src);
            const work = Main.layoutManager.getWorkAreaForMonitor(monitor);
            const [, srcY] = src.get_transformed_position();
            const stageX = work.x - this._zxpOx;
            const stageY = srcY - box.get_height() + this._zxpOb;
            this.setArrowOrigin(0);
            let parent = this.get_parent();
            let ok = false, x = 0, y = 0;
            while (!ok && parent) {
                [ok, x, y] = parent.transform_stage_point(stageX, stageY);
                parent = parent.get_parent();
            }
            box.set_origin(Math.floor(x), Math.floor(y));
            debug(`posição: ${Math.floor(x)},${Math.floor(y)} altura=${box.get_height()} barra=${srcY} ` +
                `ox=${this._zxpOx} ob=${this._zxpOb} trans=${this.translation_x},${this.translation_y}`);
        };
        // medir os desvios internos e repor a posição se mudarem
        const measure = () => {
            bp._zxpIdle = 0;
            if (!bp.visible || !layout._zxpHeader?.get_stage() || !layout._zxpFooter)
                return GLib.SOURCE_REMOVE;
            const [bx, by] = bp.get_transformed_position();
            const [hx] = layout._zxpHeader.get_transformed_position();
            const [, fy] = layout._zxpFooter.get_transformed_position();
            const ox = Math.round(hx - bx);
            const ob = Math.round((by + bp.height) - (fy + layout._zxpFooter.height));
            debug(`medida: ox=${ox} ob=${ob} bp=${bx},${by} ${bp.width}x${bp.height} layout=${layout.height}`);
            if (ox !== bp._zxpOx || ob !== bp._zxpOb) {
                bp._zxpOx = ox;
                bp._zxpOb = ob;
                bp.queue_relayout();
            }
            return GLib.SOURCE_REMOVE;
        };
        const queue = () => {
            if (!bp._zxpIdle)
                bp._zxpIdle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, measure);
        };
        bp.connectObject('notify::allocation', queue, 'notify::visible', queue, layout);
        layout.connectObject('destroy', () => {
            if (bp._zxpIdle)
                GLib.source_remove(bp._zxpIdle);
            bp._zxpIdle = 0;
            delete bp._reposition;
            bp._zxpPinned = false;
        }, layout);
        bp.queue_relayout();
    }

    _patch(proto, name, wrapper) {
        const orig = proto[name];
        if (typeof orig !== 'function')
            return;
        proto[name] = function (...args) {
            return wrapper.call(this, orig, ...args);
        };
        this._patches.push([proto, name, orig]);
    }

    // Reconstrói os menus já criados com a disposição atual (patch ativo ou não)
    _reloadMenus() {
        const panels = global.zorinTaskbar?.panels?.map(p => p?.panel) ?? [Main.panel];
        for (const panel of panels) {
            const button = panel?.statusArea?.['zorin-menu'];
            button?.menu?._reloadLayout?.();
        }
    }

    _xpify(layout) {
        if (layout._zxp)
            return;
        const left = layout._leftBox;
        const sep = layout._verticalSeparator?.actor;
        const sidebar = layout._sidebar;
        if (!left || !sidebar)
            return;
        layout._zxp = true;

        // Corpo: as duas colunas lado a lado
        const body = layout._zxpBody = new St.BoxLayout({
            style_class: 'zxp-start-body',
            x_expand: true,
            y_expand: true,
        });
        for (const a of [left, sep, sidebar]) {
            if (a && a.get_parent() === layout)
                layout.remove_child(a);
        }
        body.add_child(left);
        body.add_child(sidebar);
        sep?.destroy();
        left.add_style_class_name('zxp-start-left');
        sidebar.add_style_class_name('zxp-start-right');
        // medidas inline: a folha do zorin-menu é carregada depois do tema e ganha-lhe
        left.set_style(`padding: ${LEFT_PAD_T}px 4px ${LEFT_PAD_B}px 6px;`);
        sidebar.set_style('padding: 9px 8px 5px 6px;');
        left.set_width(LEFT_W);      // largura fixa (o CSS só dá a preferida)
        const catBox = layout._categoriesSection?._categoriesBox;
        if (catBox) {
            for (const c of catBox.get_children())
                c._arrowIcon?.hide();
            catBox.connectObject('child-added', (_b, c) => c._arrowIcon?.hide(), layout);
        }
        const catScroll = layout._categoriesSection?._scrollBox;
        if (catScroll) {
            // sem scroll: a lista de categorias mede e mostra o conteúdo todo
            catScroll.vscrollbar_policy = St.PolicyType.NEVER;
            catScroll.remove_style_class_name('vfade');
        }
        sidebar.set_width(RIGHT_W);

        layout.vertical = true;
        layout.add_style_class_name('zxp-start');
        layout.add_child(layout._zxpHeader = this._header(sidebar));
        // Sombra do XP (desenhada pelo win32k, não vem no tema; medida numa
        // captura real): 5 px de padding à direita e em baixo, com a imagem de
        // fundo gerada em updateHeight. Fica dentro da caixa do menu: o
        // BoxPointer é pintado num buffer próprio e o que sai da caixa perde-se
        layout.set_style(`padding: 0 ${SHADOW_W}px ${SHADOW_W}px 0;`);
        layout.add_child(body);
        layout.add_child(layout._zxpFooter = this._footerBox = this._footer(layout));

        // O utilizador e os botões de sessão passam para as faixas. O
        // updateHeight do Zorin volta a mostrar o utilizador para medir a
        // altura: esconde-se de novo depois de cada chamada.
        const kids = sidebar.get_children();
        const sessionSep = kids[kids.indexOf(sidebar._sessionButtonsSection) - 1];
        const hideMoved = () => {
            sidebar._userItem?.hide();
            sidebar._userSeparator?.hide();
            sidebar._sessionButtonsSection?.hide();
            sessionSep?.hide();
        };
        hideMoved();
        const origUpdate = sidebar.updateHeight.bind(sidebar);
        sidebar.updateHeight = available => {
            origUpdate(available);
            hideMoved();
            // Altura fixa, como no XP: a da vista de categorias (todas, sem
            // scroll), seja qual for a vista atual — ao abrir uma categoria ou
            // pesquisar, as listas maiores rolam dentro da coluna e o menu não salta
            const cats = layout._categoriesSection?._categoriesBox;
            const all = layout._allAppsButton;
            let natLeft = LEFT_PAD_T + LEFT_PAD_B;
            if (cats)
                natLeft += cats.get_preferred_height(LEFT_W)[1];
            if (all)
                natLeft += all.get_preferred_height(LEFT_W)[1] + LEFT_SEP_H;
            const [, natRight] = sidebar.get_preferred_height(RIGHT_W);
            return Math.min(available, Math.max(natRight, natLeft));
        };

        this._xpPlaces(sidebar);
        this._xpShortcuts(sidebar);
        // Coluna direita com as medidas do XP (Screenshot_20261011171012):
        // itens de 26 px (ícone a 1 px do topo e a 2 px da esquerda, texto 4 px
        // depois do ícone) com 4 px entre eles; separadores de 12 px com a linha
        // (StartPanel.PlacesListSeparator, 134×2, tamanho real) 7 px abaixo do
        // item anterior e em x=28. O espaço que sobra fica em baixo, como no XP.
        // Tudo inline: a folha do zorin-menu ganha ao tema nestes seletores
        const xpRight = a => {
            if (a.has_style_class_name?.('popup-separator-menu-item')) {
                a.set_style('padding: 3px 0 3px 0; margin: 0; min-height: 0; spacing: 0;');
                const line = a._separator ??
                    a.get_children().find(c => c.has_style_class_name?.('popup-separator-menu-item-separator'));
                if (line) {
                    line.x_expand = false;
                    line.x_align = Clutter.ActorAlign.START;
                    line.set_width(134);
                    line.set_style('height: 2px; margin: 0 0 0 22px; padding: 0; background-size: 134px 2px;');
                }
                return;
            }
            if (a.has_style_class_name?.('popup-menu-item')) {
                a.y_expand = false;
                a.set_style('padding: 1px 4px 1px 2px; spacing: 4px; margin: 0 0 4px 0;');
                return;
            }
            if (a !== sidebar && a instanceof St.BoxLayout) {
                a.y_expand = false;
                a.set_style('padding: 0; margin: 0; spacing: 0;');
            }
            for (const c of a.get_children())
                xpRight(c);
        };
        xpRight(sidebar);

        this._xpMorePrograms(layout, left);
        this._xpScrollBars(layout);

        // Pesquisa do Zorin na faixa de baixo, à esquerda (como na montagem)
        const search = layout._searchEntry;
        if (search) {
            search.get_parent()?.remove_child(search);
            search.add_style_class_name('zxp-start-search');
            search.set_style('margin: 0; border-radius: 3px;');
            search.set_position(SEARCH_X, Math.floor((FOOTER_H - SEARCH_H) / 2));
            search.set_size(SEARCH_W, SEARCH_H);
            this._footerBox.add_child(search);
            // Sempre oculta (a faixa de baixo do XP só tem Terminar sessão e
            // Encerrar), mas operacional: com o menu aberto, qualquer tecla
            // começa a pesquisa no Zorin e os resultados aparecem à esquerda
            search.opacity = 0;
            search.reactive = false;
        }
    }

    // "Todos os programas" como no XP: separador por cima, texto a negrito
    // (#373738) alinhado à direita e a seta verde (StartPanel.MoreProgramsArrow
    // / hot) a 8 px da borda; o destaque ocupa 175×24, de x=7 até à seta.
    // "Voltar" é o espelho: mesma altura, letra e destaque, seta para a esquerda
    _xpMorePrograms(layout, left) {
        // separador do XP por cima de "Todos os programas" e de "Voltar"
        // (cada um só visível quando o respetivo botão está visível)
        for (const btn of [layout._allAppsButton, layout._backButton]) {
            if (!btn)
                continue;
            const sep = this._xpLeftSeparator(XP_DIR);
            left.insert_child_below(sep, btn);
            btn.bind_property('visible', sep, 'visible', GObject.BindingFlags.SYNC_CREATE);
        }
        // "Todos os programas" com p minúsculo, como no XP (o Zorin escreve "Programas")
        this._xpGreenButton(layout._allAppsButton, 'Todos os programas', 'start-more-arrow', false);
        this._xpGreenButton(layout._backButton, 'Voltar', 'start-back-arrow', true);
    }

    _xpGreenButton(btn, text, arrowName, arrowFirst) {
        if (!btn)
            return;
        btn.add_style_class_name('zxp-more-programs');
        // inline: a folha do zorin-menu ganha ao tema no padding dos itens
        btn.set_style('padding: 0; margin: 0 4px 0 1px; spacing: 12px; min-height: 24px; border-radius: 0;');
        btn._icon?.hide();
        const label = btn.get_children().find(c => c instanceof St.Label);
        if (label) {
            label.text = text;
            label.x_expand = true;
            label.x_align = arrowFirst ? Clutter.ActorAlign.START : Clutter.ActorAlign.END;
            label.y_align = Clutter.ActorAlign.CENTER;
        }
        // seta no tamanho original (16×24): um St.Icon quadrado deformava-a
        const arrowStyle = h => `background-image: url("file://${XP_DIR}/${arrowName}${h ? '-hot' : ''}.png"); ` +
            'background-size: 16px 24px; background-repeat: no-repeat;';
        const arrow = new St.Widget({
            width: 16,
            height: 24,
            y_align: Clutter.ActorAlign.CENTER,
            style: arrowStyle(false),
        });
        if (arrowFirst)
            btn.insert_child_at_index(arrow, 0);
        else
            btn.add_child(arrow);
        // seta "hot" com o realce: rato por cima ou item escolhido pelo teclado
        const hot = () => {
            const style = arrowStyle(btn.hover || btn.has_style_class_name('selected'));
            if (arrow.style !== style)
                arrow.style = style;
        };
        btn.connectObject('notify::hover', hot, 'style-changed', hot, arrow);
    }

    // Barras de deslocamento do XP nas listas da coluna esquerda: ocupam 17 px
    // (não ficam por cima da lista, sem esbatimento) e as setas, que o tema
    // desenha na border-image, funcionam como no Windows: um clique avança uma
    // linha e, mantendo premido, repete
    _xpScrollBars(layout) {
        const walk = a => {
            if (a instanceof St.ScrollView)
                this._xpScrollBar(a, layout);
            for (const c of a.get_children())
                walk(c);
        };
        walk(layout);
    }

    _xpScrollBar(view, layout) {
        const bar = view.get_vscroll_bar?.() ?? view.vscroll;
        if (!bar || bar._zxp)
            return;
        bar._zxp = true;
        view.overlay_scrollbars = false;
        view.remove_style_class_name('vfade');
        bar.z_position = 0;
        bar.reactive = true;
        const handle = bar.get_children().find(c => c.name === 'vhandle');
        let zone = null, pressed = null, timer = 0, grab = null;

        // Barra (setas + calha) e cursor (com a pega centrada, se couber)
        // como imagens do tamanho exato, trocadas conforme o estado
        const paint = () => {
            const h = Math.round(bar.height);
            if (h >= 2 * ARROW_H) {
                let state = 'normal';
                if (pressed && zone === pressed)
                    state = `${pressed}-active`;
                else if (!pressed && zone)
                    state = `${zone}-hover`;
                const img = slicedImage(`scroll-vbar-${state}`, 17, h, [ARROW_H, 0, ARROW_H, 0]);
                const style = `background-image: url("file://${img}"); background-position: 0 0;`;
                if (bar.get_style() !== style)
                    bar.set_style(style);
            }
            const th = Math.round(handle?.height ?? 0);
            if (handle && th >= 10) {
                const state = handle.has_style_pseudo_class('active') ? 'active'
                    : handle.hover ? 'hover' : 'normal';
                // a pega só aparece se couber nas margens do cursor (4 + 8 + 4)
                const img = slicedImage(`scroll-thumb-${state}`, 17, th, [5, 5, 5, 5],
                    th >= 16 ? `scroll-grip-${state}` : null);
                const style = `background-image: url("file://${img}"); background-position: 0 0;`;
                if (handle.get_style() !== style)
                    handle.set_style(style);
            }
        };
        const zoneAt = event => {
            const [sx, sy] = event.get_coords();
            const [ok, x, y] = bar.transform_stage_point(sx, sy);
            if (!ok || x < 0 || x >= bar.width)
                return null;
            if (y >= 0 && y < ARROW_H)
                return 'up';
            if (y >= bar.height - ARROW_H && y < bar.height)
                return 'down';
            return null;
        };
        // uma linha = a altura de um item da lista
        const line = () => {
            const find = a => {
                if (a.visible && a.has_style_class_name?.('popup-menu-item') && a.height > 0)
                    return a.height;
                for (const c of a.get_children()) {
                    const h = find(c);
                    if (h)
                        return h;
                }
                return 0;
            };
            return find(view) || bar.adjustment.step_increment;
        };
        // só avança com o botão premido em cima da seta onde se carregou
        const step = () => {
            if (!pressed || zone !== pressed)
                return;
            const adj = bar.adjustment;
            const v = adj.value + (pressed === 'up' ? -line() : line());
            adj.value = Math.max(adj.lower, Math.min(adj.upper - adj.page_size, v));
        };
        const stop = () => {
            if (timer)
                GLib.source_remove(timer);
            timer = 0;
            grab?.dismiss();
            grab = null;
            pressed = null;
            for (const a of view.get_actions())
                a.enabled = true;
            paint();
        };
        bar.connectObject(
            'motion-event', (_a, event) => {
                zone = zoneAt(event);
                paint();
                return Clutter.EVENT_PROPAGATE;
            },
            'leave-event', () => {
                if (!pressed) {
                    zone = null;
                    paint();
                }
                return Clutter.EVENT_PROPAGATE;
            },
            'button-press-event', (_a, event) => {
                if (event.get_button() !== Clutter.BUTTON_PRIMARY || pressed)
                    return Clutter.EVENT_PROPAGATE;
                zone = zoneAt(event);
                if (!zone)
                    return Clutter.EVENT_PROPAGATE;
                pressed = zone;
                // captura o rato até largar o botão (mesmo fora da barra),
                // como o St faz ao arrastar o cursor; o gesto de arrastar a
                // lista (PanAction do Zorin) fica desligado entretanto
                const focus = global.stage.key_focus;
                if (focus && focus !== layout && layout.contains(focus))
                    global.stage.set_key_focus(layout);
                grab = global.stage.grab(bar);
                for (const a of view.get_actions())
                    a.enabled = false;
                paint();
                step();
                // repetição: a primeira ao fim de ~1/3 s, depois a cada 50 ms
                timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 330, () => {
                    timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                        step();
                        return GLib.SOURCE_CONTINUE;
                    });
                    step();
                    return GLib.SOURCE_REMOVE;
                });
                return Clutter.EVENT_STOP;
            },
            'button-release-event', () => {
                if (!pressed)
                    return Clutter.EVENT_PROPAGATE;
                stop();
                return Clutter.EVENT_STOP;
            },
            'notify::height', paint,
            layout);
        handle?.connectObject('notify::height', paint, 'notify::hover', paint,
            'style-changed', paint, layout);
        layout.connectObject('destroy', stop, bar);
        view.connectObject('notify::mapped', () => {
            if (!view.mapped)
                stop();
        }, layout);
        paint();
    }

    // Separador do XP (StartPanel.ProgListSeparator, 172×2) com a imagem em x=12
    // (a parte visível vai de 18 a 177, como na captura), 10 px no total
    _xpLeftSeparator(xp) {
        const line = new St.Widget({
            width: 172,
            height: 2,
            x_expand: true,
            x_align: Clutter.ActorAlign.START,
            style: `background-image: url("file://${xp}/start-sep-left.png"); ` +
                'background-size: 172px 2px; background-repeat: no-repeat;',
        });
        return new St.Bin({
            child: line,
            x_expand: true,
            style: 'padding: 3px 0 5px 6px;',
        });
    }

    _icon(key) {
        const path = `${XP_DIR}/start-ico-${key}.png`;
        return Gio.FileIcon.new(Gio.File.new_for_path(path));
    }

    // Locais como no XP, pela ordem escolhida pelo utilizador e com os ícones
    // de 24 px do XP; os restantes (Transferências, etc.) ficam escondidos.
    // "O meu computador" abre a pasta pessoal.
    _xpPlaces(sidebar) {
        const places = sidebar._placesSection;
        const items = places?._items;
        if (!items)
            return;
        places.add_style_class_name('zxp-places');
        const dir = d => GLib.get_user_special_dir(d);
        const U = GLib.UserDirectory;
        const order = [
            [dir(U.DIRECTORY_DOCUMENTS), 'Os meus documentos', 'documents'],
            [dir(U.DIRECTORY_DESKTOP), 'Ambiente de trabalho', 'desktop'],
            [dir(U.DIRECTORY_PICTURES), 'As minhas imagens', 'pictures'],
            [dir(U.DIRECTORY_MUSIC), 'A minha música', 'music'],
            [GLib.get_home_dir(), 'O meu computador', 'computer'],
        ];
        const byPath = new Map(items.map(it => [it._info?.file?.get_path?.(), it]));
        for (const it of items)
            places.remove_child(it);
        const shown = new Set();
        for (const [path, label, key] of order) {
            const it = byPath.get(path);
            if (!it || shown.has(it))
                continue;
            shown.add(it);
            places.add_child(it);
            const apply = () => {
                it._label.text = label;
                it._icon.gicon = this._icon(key);
                it._icon.icon_size = 24;
            };
            // o Zorin atualiza nome/ícone de forma assíncrona: reaplicar depois
            it._info.connectObject('changed', apply, it);
            apply();
        }
        for (const it of items) {
            if (!shown.has(it)) {
                places.add_child(it);
                it.hide();
            }
        }
    }

    // Atalhos com ícones do XP (escolhidos pelo utilizador) e, depois de um
    // segundo separador, Ajuda e suporte, Internet (globo do XP, navegador
    // predefinido) e o Terminal com o ícone da Linha de comandos (cmd.exe)
    _xpShortcuts(sidebar) {
        const shortcuts = sidebar._shortcutsSection;
        if (shortcuts && this._misc?.ShortcutMenuItem) {
            const closeMenu = item => {
                let a = item;
                while (a && !a._delegate?.close)
                    a = a.get_parent();
                a?._delegate?.close();
            };
            const add = (label, command, key) => {
                const it = new this._misc.ShortcutMenuItem(label, command, 'application-x-executable-symbolic');
                it._icon.gicon = this._icon(key);
                it._icon.icon_size = 24;
                it.connect('activated', () => closeMenu(it));
                shortcuts.add_child(it);
                return it;
            };
            shortcuts.add_child(new PopupMenu.PopupSeparatorMenuItem());
            // Internet: o navegador predefinido (lido no momento do clique)
            const net = add('Internet', ['true'], 'internet');
            net.activate = event => {
                const app = Gio.AppInfo.get_default_for_uri_scheme('https');
                app?.launch([], global.create_app_launch_context(event?.get_time?.() ?? 0, -1));
                net.emit('activated');
            };
            // Downloads: a pasta das transferências (lida no momento do clique:
            // pode ter mudado de sítio depois de o menu ser feito)
            const downloads = add('Downloads', ['true'], 'downloads');
            downloads.activate = event => {
                GLib.reload_user_special_dirs_cache();
                const path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) ??
                    GLib.get_home_dir();
                try {
                    Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(path).get_uri(),
                        global.create_app_launch_context(event?.get_time?.() ?? 0, -1));
                } catch (e) {
                    console.warn(`Zorin XP: Downloads: ${e.message}`);
                }
                downloads.emit('activated');
            };
            add('Terminal', ['x-terminal-emulator'], 'terminal');
        }
        const icons = {
            'gnome-software': 'programs',
            'gnome-control-center': 'settings',
            'zorin-appearance': 'appearance',
        };
        const walk = a => {
            const key = icons[a._command?.[0]];
            if (key && a._icon) {
                a._icon.gicon = this._icon(key);
                a._icon.icon_size = 24;
            }
            for (const c of a.get_children())
                walk(c);
        };
        walk(sidebar);
    }

    _header() {
        const header = new St.Widget({style_class: 'zxp-start-header', x_expand: true, height: HEADER_H,
            layout_manager: new Clutter.FixedLayout()});
        const tile = new St.Bin({style_class: 'zxp-start-usertile', x: 1, y: 1});
        const user = AccountsService.UserManager.get_default().get_user(GLib.get_user_name());
        const pic = new St.Bin({style_class: 'zxp-start-userpic', width: 48, height: 48});
        tile.set_child(pic);
        const name = new St.Label({style_class: 'zxp-start-username', x: 67, y: 20});
        const sync = () => {
            const file = user.get_icon_file?.();
            if (file && GLib.file_test(file, GLib.FileTest.EXISTS)) {
                pic.set_child(null);
                pic.style = `background-image: url("file://${file}"); background-size: 48px 48px;`;
            } else {
                pic.style = 'background-color: #ffffff;';
                pic.set_child(new St.Icon({icon_name: 'avatar-default-symbolic', icon_size: 40,
                    style_class: 'zxp-start-noavatar'}));
            }
            name.text = user.get_real_name() || user.get_user_name() || GLib.get_user_name();
        };
        user.connectObject('changed', sync, header);
        if (user.is_loaded)
            sync();
        else
            user.connectObject('notify::is-loaded', sync, header);
        header.add_child(tile);
        header.add_child(name);
        return header;
    }

    _footer(layout) {
        const footer = new St.Widget({style_class: 'zxp-start-footer', x_expand: true, height: FOOTER_H,
            layout_manager: new Clutter.FixedLayout()});
        const actions = SystemActions.getDefault();
        // como no XP: o Iniciar fecha primeiro (de imediato, sem animação) e só
        // depois aparece o diálogo de desligar/terminar sessão
        const close = () => closeStartMenus();
        const mk = (x, icon, text, fn) => {
            const b = new St.Button({style_class: 'zxp-start-session', x, y: 8, can_focus: true,
                track_hover: true});
            const box = new St.BoxLayout({style_class: 'zxp-start-session-box'});
            const ic = new St.Bin({style_class: `zxp-start-session-icon zxp-${icon}`, width: 24, height: 24});
            box.add_child(ic);
            box.add_child(new St.Label({text, y_align: Clutter.ActorAlign.CENTER}));
            b.set_child(box);
            b.connect('clicked', () => {
                close();
                fn();
            });
            return b;
        };
        // o diálogo do XP abre logo a seguir ao Iniciar fechar (sem passar pelo
        // gnome-session); sem a extensão de fim de sessão, os do GNOME
        footer.add_child(mk(LOGOFF_X, 'logoff', 'Terminar sessão',
            () => showEndSession(LOGOUT) || actions.activateLogout()));
        footer.add_child(mk(SHUTDOWN_X, 'shutdown', 'Encerrar',
            () => showEndSession(SHUTDOWN) || actions.activatePowerOff()));
        return footer;
    }

    destroy() {
        this._destroyed = true;
        for (const [proto, name, orig] of this._patches.reverse())
            proto[name] = orig;
        this._patches = [];
        this._reloadMenus();
    }
}
