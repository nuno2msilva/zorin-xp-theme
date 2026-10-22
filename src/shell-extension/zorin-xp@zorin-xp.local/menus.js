/*
 * Menus de contexto do Shell (barra de tarefas, ícones da área de
 * notificação, menus das aplicações) com o aspeto dos menus do XP: caixa
 * branca quadrada, contorno #ACA899, realce #316AC5, itens de 17 px.
 *
 * O CSS só chega aos menus marcados com .zxp-menu: os painéis do GNOME que
 * também são PopupMenu (definições rápidas, calendário, menu Iniciar) têm
 * aspeto próprio e ficam de fora.
 */
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const SKIP_MENUS = ['QuickSettingsMenu'];
const SKIP_SOURCES = ['DateMenuButton', 'QuickSettings'];

function isXpMenu(menu) {
    if (SKIP_MENUS.includes(menu.constructor.name))
        return false;
    if (SKIP_SOURCES.includes(menu.sourceActor?.constructor?.name))
        return false;
    return !menu.actor.has_style_class_name('zorin-menu');
}

// itens com marca (visto, ponto): a marca ocupa a coluna de 17 px à
// esquerda do texto, como no XP
function markOrnaments(menu) {
    for (const item of menu._getMenuItems()) {
        if (item instanceof PopupMenu.PopupMenuSection)
            markOrnaments(item);
        else if (item._ornamentIcon)
            item[item._ornamentIcon.visible ? 'add_style_class_name' : 'remove_style_class_name']('zxp-ornamented');
    }
}

// títulos de secção (separadores com texto): os menus do XP não os tinham,
// e no separador de 7 px o texto ficava cortado pela linha. O "Janelas
// abertas" do menu das aplicações (barra de tarefas) sai de todo — fica só a
// lista das janelas, separada do resto; nos outros menus fica só a linha.
function dropHeadings(menu, touched) {
    const header = menu._openWindowsHeader;
    for (const item of menu._getMenuItems()) {
        if (item instanceof PopupMenu.PopupMenuSection) {
            dropHeadings(item, touched);
        } else if (item instanceof PopupMenu.PopupSeparatorMenuItem && item.label.text && !touched.has(item)) {
            touched.set(item, item.connect('destroy', () => touched.delete(item)));
            item.label.visible = false;
            if (item === header) {
                // (o GNOME mostra-o e esconde-o com as janelas: fica sem altura)
                item._separator.visible = false;
                item.add_style_class_name('zxp-gone');
            }
        }
    }
}

export class MenuTweaks {
    constructor() {
        const proto = PopupMenu.PopupMenu.prototype;
        this._origOpen = proto.open;
        const origOpen = this._origOpen;
        const touched = this._touched = new Map();      // item -> sinal destroy
        proto.open = function (...args) {
            if (isXpMenu(this)) {
                this.actor.add_style_class_name('zxp-menu');
                markOrnaments(this);
                dropHeadings(this, touched);
            }
            return origOpen.apply(this, args);
        };
    }

    destroy() {
        PopupMenu.PopupMenu.prototype.open = this._origOpen;
        for (const [item, id] of this._touched) {
            item.disconnect(id);
            item.label.visible = item.label.text !== '';
            item._separator.visible = true;
            item.remove_style_class_name('zxp-gone');
        }
        this._touched.clear();
    }
}
