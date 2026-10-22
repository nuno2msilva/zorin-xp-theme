/*
 * Geometria dos botões da barra de tarefas como no Windows XP.
 *
 * A zorin-taskbar define por código (estilo inline) o tamanho do ícone e as
 * margens dos botões, e desenha indicadores de execução; o CSS do tema não
 * os consegue alterar. Aqui ajustam-se esses métodos em tempo de execução
 * (os ficheiros do sistema não são tocados). Medidas tiradas de capturas
 * reais do XP (barra de 30 px):
 *   botão 160×30 sem espaço entre botões, ícone 16×16 em (11, 8),
 *   texto a partir de x = 31, sem pontos/realces de execução.
 */
import Clutter from 'gi://Clutter';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {XP_DIR, savedImage, slicedImage} from './images.js';

const TASKBAR_UUID = 'zorin-taskbar@zorinos.com';
const ICON_SIZE = 16;
const ICON_PADDING = 'padding: 8px 4px 6px 11px;';  // 11 + 16 + 4 = 31 px até ao texto

// Área de notificação (TrayNotifyHoriz, medida em capturas do XP): a seta
// "mostrar ícones ocultos" (19×20) no início da área, centrada na borda
// curva; ícones de 16 px com passo de 18 a partir de x=19 (ContentMargins);
// ao abrir, os ícones ocultos voltam a esconder-se 2 s depois de o rato sair
// da área, como no XP
const TRAY_PAD_L = 19;
const ICON_GAP = 2;
const COLLAPSE_MS = 2000;
// "Ver ADT" (botão Mostrar ambiente de trabalho da zorin-taskbar): invisível e
// sem ocupar lugar, só uma zona de clique sobre o canto inferior direito
const DESKTOP_HIT_W = 4;
const DESKTOP_STYLE = 'width: 0; padding: 0; margin: 0; border: 0; background: none;';
const SLIDE_MS = 250;   // os ícones ocultos deslizam a partir da seta
// atividade da rede: quanto tempo (ms, ao acaso no intervalo) cada estado dos
// ecrãs dos monitores se mantém — apagados ~2 s, acesos um pouco mais
const NET_OFF_MS = [1500, 2500];
const NET_ON_MS = [2500, 4000];

// Bytes recebidos e enviados pelas placas de rede físicas (contadores do
// kernel em /sys/class/net: sem capturar pacotes nem permissões especiais).
// As virtuais (lo, docker, pontes, VirtualBox) não têm "device" e ficam de fora
let _ifaces = null, _ifacesAt = 0;
const _decoder = new TextDecoder();
function netCounters() {
    const now = GLib.get_monotonic_time();
    if (!_ifaces || now - _ifacesAt > 5000000) {
        _ifacesAt = now;
        _ifaces = [];
        try {
            const en = Gio.File.new_for_path('/sys/class/net').enumerate_children(
                'standard::name', Gio.FileQueryInfoFlags.NONE, null);
            for (let info; (info = en.next_file(null));) {
                const n = info.get_name();
                if (n !== 'lo' && GLib.file_test(`/sys/class/net/${n}/device`, GLib.FileTest.EXISTS))
                    _ifaces.push(n);
            }
            en.close(null);
        } catch (e) {
            return null;
        }
    }
    let rx = 0, tx = 0;
    for (const n of _ifaces) {
        try {
            const [, r] = GLib.file_get_contents(`/sys/class/net/${n}/statistics/rx_bytes`);
            const [, t] = GLib.file_get_contents(`/sys/class/net/${n}/statistics/tx_bytes`);
            rx += Number(_decoder.decode(r));
            tx += Number(_decoder.decode(t));
        } catch (e) {
            // a placa desapareceu: a lista é refeita daqui a pouco
        }
    }
    return [rx, tx];
}

// Ícone do XP (tray-ico-*.png, extraídos de stobject/netshell/sapi/intl/
// irprops/batmeter) para um ícone de estado do GNOME; null = não havia no XP
function xpTrayIcon(name) {
    const n = name.replace(/-symbolic$/, '');
    if (n.startsWith('audio-volume-'))
        return n.includes('muted') ? 'volume-muted' : 'volume';
    if (n.startsWith('audio-input-microphone') || n.startsWith('microphone-sensitivity'))
        return 'mic';
    if (n.startsWith('location-services'))
        return 'location';
    if (n.startsWith('bluetooth'))
        return 'bluetooth';
    if (/^network-(wireless|wired|cellular)|^network-offline/.test(n)) {
        if (/acquiring|no-route/.test(n))
            return 'network-busy';
        if (/offline|disconnected|disabled/.test(n))
            return 'network-off';
        return 'network';    // o XP usa os dois monitores também na rede sem fios
    }
    if (n.startsWith('battery')) {
        if (/charging|charged/.test(n))
            return 'battery-ac';     // ligado à corrente: ficha com bateria
        if (n.includes('missing'))
            return 'battery-missing';
        const m = /battery-level-(\d+)/.exec(n);
        if (m) {
            const v = Number(m[1]);
            return v >= 60 ? 'battery-full' : v >= 30 ? 'battery-half' : v > 10 ? 'battery-low' : 'battery-empty';
        }
        if (n.includes('full'))
            return 'battery-full';
        if (n.includes('good'))
            return 'battery-half';
        if (n.includes('low'))
            return 'battery-low';
        if (/caution|empty/.test(n))
            return 'battery-empty';
        return 'battery-unknown';
    }
    return null;
}

// --- Ícones das aplicações a cores, como no XP -----------------------------
// Muitas apps (Claude, Telegram, LocalSend…) dão à área de notificação um
// ícone monocromático. Se o ícone não tiver cor, usa-se o ícone da própria
// aplicação; os pormenores coloridos do original (p. ex. a bolinha vermelha
// de mensagens por ler) ficam por cima. Os que já têm cor ficam como estão.
// Apps cujo ícone monocromático fica como está (o a cores não contrasta com o
// azul da área de notificação)
const TRAY_KEEP_ORIGINAL = ['org.localsend.localsend_app'];

let _iconTheme = null;
function iconPixbuf(gicon, size) {
    try {
        if (gicon instanceof Gio.ThemedIcon) {
            _iconTheme ??= new St.IconTheme();
            const file = _iconTheme.lookup_by_gicon(gicon, size, St.IconLookupFlags.FORCE_SIZE)?.get_filename();
            return file ? GdkPixbuf.Pixbuf.new_from_file_at_size(file, size, size) : null;
        }
        if (gicon instanceof Gio.FileIcon)
            return GdkPixbuf.Pixbuf.new_from_file_at_size(gicon.get_file().get_path(), size, size);
        if (gicon.load) {
            const [stream] = gicon.load(size, null);
            return GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size, size, true, null);
        }
    } catch (e) {
        console.warn(`Zorin XP: ícone da área de notificação: ${e}`);
    }
    return null;
}

const isColored = (r, g, b) => {
    const mx = Math.max(r, g, b);
    return mx > 0 && (mx - Math.min(r, g, b)) / mx > 0.3;
};

// Píxeis opacos e com cor: [com cor, opacos]
function colorStats(pb) {
    const px = pb.get_pixels(), n = pb.get_n_channels(), rs = pb.get_rowstride();
    let colored = 0, total = 0;
    for (let y = 0; y < pb.get_height(); y++) {
        for (let x = 0; x < pb.get_width(); x++) {
            const o = y * rs + x * n;
            if (n === 4 && px[o + 3] < 128)
                continue;
            total++;
            if (isColored(px[o], px[o + 1], px[o + 2]))
                colored++;
        }
    }
    return [colored, total];
}

// Aplicação dona do indicador: a que a extensão de indicadores já conhece ou,
// se não (apps Flatpak), procurada pelo nome do ícone e pelo identificador
const _appCache = new Map();
function trayApp(indicator, gicon) {
    if (indicator?._appInfo?.get_icon?.())
        return indicator._appInfo;
    const cands = [];
    const add = s => {
        if (!s)
            return;
        let c = String(s).replace(/\.(png|svg)$/, '');
        for (let prev; prev !== c;) {
            prev = c;
            c = c.replace(/-symbolic$/, '')
                .replace(/[-_](tray|panel|indicator|mute|muted|attention|unread|active|inactive|dark|light)$/i, '')
                .replace(/_status_icon_\d+$/i, '');
        }
        cands.push(c);
    };
    if (gicon instanceof Gio.ThemedIcon)
        gicon.get_names().forEach(add);
    add(indicator?.id);
    add(indicator?.title);
    const key = cands.join('|');
    if (_appCache.has(key))
        return _appCache.get(key);
    const apps = Gio.AppInfo.get_all();
    let found = null;
    for (const c of cands) {
        const lc = c.toLowerCase();
        if (lc.length < 3)
            continue;
        const id = a => (a.get_id() ?? '').toLowerCase().replace(/\.desktop$/, '');
        for (const match of [
            a => id(a) === lc,
            a => (a.get_startup_wm_class?.() ?? '').toLowerCase() === lc,
            a => (a.get_name() ?? '').toLowerCase() === lc,
            a => lc.length >= 4 && id(a).includes(lc),
        ]) {
            found = apps.find(a => match(a) && a.get_icon());
            if (found)
                break;
        }
        if (found)
            break;
    }
    _appCache.set(key, found);
    return found;
}

// Ícone a cores para o ícone da área de notificação, ou null para o manter
function coloredTrayIcon(indicator, gicon) {
    const orig = iconPixbuf(gicon, 16);
    if (!orig)
        return null;
    const [colored, total] = colorStats(orig);
    if (!total || colored / total >= 0.25)
        return null;            // já tem cor
    const app = trayApp(indicator, gicon);
    if (TRAY_KEEP_ORIGINAL.includes((app?.get_id() ?? '').replace(/\.desktop$/, '')))
        return null;
    const appIcon = app?.get_icon();
    if (!appIcon)
        return null;
    if (!colored)
        return appIcon;
    // pormenores coloridos do original por cima do ícone da aplicação
    let base = iconPixbuf(appIcon, 16);
    if (!base)
        return appIcon;
    if (!base.get_has_alpha())
        base = base.add_alpha(false, 0, 0, 0);
    const out = base.get_pixels(), bn = base.get_n_channels(), brs = base.get_rowstride();
    const px = orig.get_pixels(), n = orig.get_n_channels(), rs = orig.get_rowstride();
    for (let y = 0; y < 16; y++) {
        for (let x = 0; x < 16; x++) {
            const o = y * rs + x * n;
            if ((n === 4 && px[o + 3] < 128) || !isColored(px[o], px[o + 1], px[o + 2]))
                continue;
            const d = y * brs + x * bn;
            out[d] = px[o];
            out[d + 1] = px[o + 1];
            out[d + 2] = px[o + 2];
            out[d + 3] = 255;
        }
    }
    const composed = GdkPixbuf.Pixbuf.new_from_bytes(new GLib.Bytes(out), GdkPixbuf.Colorspace.RGB,
        true, 8, 16, 16, brs);
    const sum = GLib.compute_checksum_for_data(GLib.ChecksumType.MD5, out);
    return Gio.FileIcon.new(Gio.File.new_for_path(savedImage(`trayapp-${sum}`, composed)));
}

// Ícone de aplicação a 16 px (o tamanho original, a pedido do utilizador em
// 2026-10-13); a separação entre eles vem de TRAY_APP_HPAD
const TRAY_APP_SIZE = 16;
// margem de cada lado dos ícones das aplicações: 2 px a mais entre eles (passo de 20)
const TRAY_APP_HPAD = 1;
function paddedTrayIcon(gicon) {
    // (os simbólicos são recoloridos pelo St: carregados à parte perdiam a cor)
    if (gicon instanceof Gio.ThemedIcon && gicon.get_names().some(n => n.endsWith('-symbolic')))
        return null;
    const pb = iconPixbuf(gicon, TRAY_APP_SIZE);
    if (!pb)
        return null;
    const canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, true, 8, 16, 16);
    canvas.fill(0);
    const src = pb.get_has_alpha() ? pb : pb.add_alpha(false, 0, 0, 0);
    const off = (16 - TRAY_APP_SIZE) / 2;
    src.copy_area(0, 0, TRAY_APP_SIZE, TRAY_APP_SIZE, canvas, off, off);
    const sum = GLib.compute_checksum_for_data(GLib.ChecksumType.MD5, canvas.get_pixels());
    return Gio.FileIcon.new(Gio.File.new_for_path(savedImage(`trayapp${TRAY_APP_SIZE}-${sum}`, canvas)));
}

// Fundo, seta e ícones ocultos da área de notificação de um painel. Os ícones
// das aplicações (#panelRight) escondem-se atrás da seta; os do sistema
// (definições rápidas) e o relógio ficam sempre à vista.
class XpTray {
    constructor(p) {
        this._p = p;
        this._right = p._rightBox ?? p.panel?._rightBox;
        this._system = p.statusArea?.quickSettings ?? null;
        this._date = p.statusArea?.dateMenu ?? null;
        this._expanded = false;
        this._touched = new Set();
        this._watched = new Set();
        this._styles = [];
        this._timer = 0;
        this._icons = new Set();
        this._boxes = new Set();
        this._appIcons = new Set();

        // O fundo vai no próprio painel interno da zorin-taskbar (transparente,
        // a toda a largura): um ator acrescentado ao painel não seria disposto
        this._panel = p.panel;
        // (o painel da zorin-taskbar só dispõe os filhos que conhece: este é
        // posto à mão em _syncBg; mexer só nele é barato, ao contrário de
        // mudar o estilo do painel, que refaz o estilo da barra inteira)
        // (restos de uma vez anterior que não se desmontou: fora)
        for (const c of this._panel.get_children()) {
            if (c.name === 'zxpTrayBg')
                c.destroy();
        }
        for (const c of this._right.get_children()) {
            if (c.has_style_class_name?.('zxp-chevron'))
                c.destroy();
        }
        this._bg = new St.Widget({reactive: false, name: 'zxpTrayBg'});
        this._panel.insert_child_at_index(this._bg, 0);
        this._chevron = new St.Button({
            style_class: 'zxp-chevron',
            reactive: true,
            can_focus: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
            accessible_name: 'Mostrar ícones ocultos',
        });
        this._chevron.connect('clicked', () => this._setExpanded(!this._expanded));
        this._right.insert_child_at_index(this._chevron, 0);
        this._right.connectObject(
            'child-added', (_b, c) => this._onAdded(c),
            'child-removed', (_b, c) => {
                this._touched.delete(c);
                this._apply();
            },
            'notify::allocation', () => this._syncBg(), this);
        this._panel.connectObject(
            'notify::allocation', () => {
                this._syncBg();
                this._syncDesktop();
            },
            'notify::style', () => this._syncBg(), this);
        for (const c of this._right.get_children())
            this._onAdded(c);

        // ícones do sistema com os do XP
        if (this._system?._indicators)
            this._hookIcons(this._system._indicators);

        // ícones do sistema seguidos, com o passo do XP, e 2 px antes do relógio
        // (2 px de margem à esquerda — o enchimento era ignorado neste botão: os
        // ícones do sistema enchem os 16 px, sem a margem transparente dos das
        // aplicações; assim o espaço visível na passagem fica igual aos outros)
        this._style(this._system, '-natural-hpadding: 0; -minimum-hpadding: 0; padding: 0; margin-left: 2px;');
        this._style(this._system?.container, `margin-right: ${ICON_GAP}px;`);
        // o -natural-hpadding não invalida a largura em cache do botão (ficavam
        // 9 px de cada lado entre os ícones das aplicações e os do sistema)
        this._system?.queue_relayout();
        // relógio como no XP em português: "0:14", sem o zero à esquerda da hora
        // e com os dois pontos normais (o GNOME escreve "00\u200e∶14": marca de
        // direção invisível e "∶", U+2236, que o Tahoma nem tem e que vinha de
        // outra fonte, mais alta)
        const clock = this._date?._clockDisplay;
        if (clock) {
            const fix = () => {
                const t = clock.text.replace(/[\u200e\u200f]/g, '').replace(/\u2236/g, ':')
                    .replace(/(^|\s)0(\d:)/, '$1$2');
                if (t !== clock.text)
                    clock.text = t;
            };
            clock.connectObject('notify::text', fix, this);
            fix();
        }
        this._apply();
    }

    // Troca os ícones de estado do GNOME pelos do XP, também nos indicadores
    // acrescentados depois e sempre que o GNOME muda o ícone
    _hookIcons(actor) {
        if (actor instanceof St.Icon) {
            this._hookIcon(actor);
            return;
        }
        if (!this._boxes.has(actor)) {
            this._boxes.add(actor);
            actor.connectObject('child-added', (_a, c) => this._hookIcons(c), this);
        }
        for (const c of actor.get_children())
            this._hookIcons(c);
    }

    _hookIcon(icon) {
        if (this._icons.has(icon))
            return;
        this._icons.add(icon);
        const sync = () => {
            const g = icon.gicon;
            if (!(g instanceof Gio.ThemedIcon))
                return;
            const key = xpTrayIcon(g.get_names()[0] ?? '');
            if (!key)
                return;
            icon._zxpOrig = g;
            icon.set_style('-st-icon-style: regular;');   // a cores, sem recolorir
            if (key === 'network') {
                // ligado: os ecrãs acendem com o tráfego (ver _netTick)
                this._netIcon = icon;
                this._setIcon(icon, icon._zxpNet ?? 'network');
                if (!this._netTimer)
                    this._scheduleNet();
                return;
            }
            if (this._netIcon === icon)
                this._netIcon = null;
            this._setIcon(icon, key);
        };
        icon.connectObject('notify::gicon', sync, this);
        sync();
    }

    // Ícones das aplicações monocromáticos -> ícone da aplicação a cores,
    // todos a 16 px
    _hookAppIcon(button) {
        const icon = button._icon;
        if (this._appIcons.has(icon))
            return;
        this._appIcons.add(icon);
        const sync = () => {
            const g = icon.gicon;
            if (!g || g === icon._zxpColor)
                return;
            icon._zxpTrayOrig = g;
            // a extensão de indicadores embrulha os ícones num EmblemedIcon (e
            // chama get_icon() sobre o atual): desembrulhar e voltar a embrulhar
            const inner = g instanceof Gio.EmblemedIcon ? g.get_icon() : g;
            const base = coloredTrayIcon(button._indicator, inner) ?? inner;
            const color = paddedTrayIcon(base) ?? (base !== inner ? base : null);
            if (color) {
                const wrapped = new Gio.EmblemedIcon({gicon: color});
                if (g instanceof Gio.EmblemedIcon)
                    g.get_emblems().forEach(e => wrapped.add_emblem(e));
                icon._zxpColor = wrapped;
                icon.gicon = wrapped;
            }
        };
        icon.connectObject('notify::gicon', sync, this);
        sync();
    }

    _setIcon(icon, key) {
        icon.gicon = Gio.FileIcon.new(Gio.File.new_for_path(`${XP_DIR}/tray-ico-${key}.png`));
    }

    _scheduleNet(key = 'network') {
        const [min, max] = key === 'network' ? NET_OFF_MS : NET_ON_MS;
        const ms = min + Math.floor(Math.random() * (max - min));
        this._netTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._netTimer = 0;
            this._netTick();
            return GLib.SOURCE_REMOVE;
        });
    }

    // Como no XP, o ecrã da frente acende quando o computador envia e o de
    // trás quando recebe. Com o tráfego contínuo de hoje ficariam sempre os
    // dois acesos: enquanto houver tráfego num sentido, o ecrã respetivo
    // acende ao acaso (mais vezes no sentido com mais tráfego), sem repetir o
    // estado anterior; sem tráfego ficam apagados
    _netTick() {
        const icon = this._netIcon;
        if (!icon) {
            this._netLast = null;
            return;
        }
        const cur = netCounters();
        let key = 'network';
        if (cur && this._netLast) {
            const dRx = Math.max(0, cur[0] - this._netLast[0]);
            const dTx = Math.max(0, cur[1] - this._netLast[1]);
            const total = dRx + dTx;
            if (total > 0) {
                const pRx = dRx ? 0.25 + 0.5 * dRx / total : 0;
                const pTx = dTx ? 0.25 + 0.5 * dTx / total : 0;
                const keyOf = (rx, tx) => rx && tx ? 'network-txrx' : tx ? 'network-tx' : rx ? 'network-rx' : 'network';
                // sorteia até sair um estado diferente do anterior (o apagado
                // também conta: é o que dá o efeito de piscar)
                for (let i = 0; i < 6 && (i === 0 || key === icon._zxpNet); i++)
                    key = keyOf(Math.random() < pRx, Math.random() < pTx);
            }
        }
        this._netLast = cur;
        if (key !== icon._zxpNet) {
            icon._zxpNet = key;
            this._setIcon(icon, key);
        }
        this._scheduleNet(key);
    }

    _style(actor, css) {
        if (!actor)
            return;
        const old = actor.get_style();
        this._styles.push([actor, old]);
        actor.set_style(`${old ?? ''}${css}`);
    }

    _items() {
        return this._right.get_children().filter(c => c !== this._chevron);
    }

    _onAdded(c) {
        if (c === this._chevron)
            return;
        // a seta é sempre o primeiro elemento
        if (this._right.get_child_at_index(0) !== this._chevron)
            this._right.set_child_at_index(this._chevron, 0);
        const button = c.get_first_child?.() ?? c;
        if (!this._watched.has(button)) {
            this._watched.add(button);
            button.connectObject('notify::visible', () => this._apply(), this);
            // os indicadores de aplicações (modo compacto) impõem por código
            // 10 px de cada lado; aqui TRAY_APP_HPAD (passo de 20)
            if (button.has_style_class_name?.('panel-button')) {
                button._zxpStyle = button.get_style();
                const fix = () => {
                    const st = button.get_style() ?? '';
                    const pad = `-natural-hpadding: ${TRAY_APP_HPAD}px; -minimum-hpadding: ${TRAY_APP_HPAD}px;`;
                    if (st.includes(pad))
                        return;
                    button.set_style(`${st.replace(/-(natural|minimum)-hpadding:[^;]*;?/g, '')}${pad}`);
                    button.queue_relayout();  // (largura em cache, ver acima)
                };
                button.connectObject('notify::style', fix, this);
                fix();
            }
            if (button._indicator && button._icon instanceof St.Icon)
                this._hookAppIcon(button);
        }
        if (!this._watched.has(c)) {
            // o GNOME volta a mostrar o contentor ao mudá-lo de painel
            this._watched.add(c);
            c.connectObject('notify::visible', () => this._apply(), this);
        }
        this._apply();
    }

    // Esconde/mostra os ícones das aplicações (o contentor de cada um só fica
    // visível se a seta estiver aberta e o ícone existir: contentores vazios
    // ocupavam 2 px). A seta só aparece se houver algum ícone para esconder;
    // sem ela, a área começa 19 px antes do 1.º ícone do sistema
    _apply() {
        if (this._applying)
            return;
        this._applying = true;
        const items = this._items();
        let any = false;
        for (const c of items) {
            const shown = (c.get_first_child?.() ?? c).visible;
            any ||= shown;
            const want = this._expanded && shown;
            this._touched.add(c);
            if (c.visible !== want && !this._sliding)
                c.visible = want;
        }
        this._chevron.visible = any;
        this._right.set_style(`padding-left: ${any ? 0 : TRAY_PAD_L}px; spacing: 0;`);
        if (this._expanded)
            this._chevron.add_style_class_name('zxp-open');
        else
            this._chevron.remove_style_class_name('zxp-open');
        this._applying = false;
        this._syncBg();
    }

    _setExpanded(expanded) {
        this._expanded = expanded;
        this._slide(expanded);
        this._apply();
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        if (!expanded)
            return;
        // fecha 2 s depois de o rato sair da área (e sem menus abertos)
        let since = null;
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            if (this._pointerInside() || this._menuOpen()) {
                since = null;
            } else {
                since ??= GLib.get_monotonic_time();
                if (GLib.get_monotonic_time() - since >= COLLAPSE_MS * 1000) {
                    this._timer = 0;
                    this._setExpanded(false);
                    return GLib.SOURCE_REMOVE;
                }
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    // Como no XP (comparado com uma gravação da área do XP): ao abrir, os
    // ícones ficam logo no sítio e a seta — com a borda do fundo claro —
    // desliza para a esquerda e vai-os destapando; ao fechar, a seta e os
    // ícones deslizam juntos para a direita e somem no limite dos ícones do
    // sistema. Nada encolhe nem estica: só translação e recorte.
    _slide(expanded) {
        this._stopSlide();
        const items = this._items().filter(c => (c.get_first_child?.() ?? c).visible);
        if (!items.length)
            return;
        this._sliding = true;
        const chev = this._chevron;
        const finish = () => {
            for (const c of items) {
                c.translation_x = 0;
                c.remove_clip();
                if (!expanded)
                    c.hide();
            }
            chev.translation_x = 0;
            this._slideItems = null;
            this._sliding = false;
            this._apply();
        };
        const run = (from, to, clip) => {
            this._slideItems = items;
            const update = () => {
                clip(chev.translation_x);
                this._syncBg();
            };
            chev.translation_x = from;
            update();
            chev.connectObject('notify::translation-x', update, this);
            chev.ease({
                translation_x: to,
                duration: SLIDE_MS,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onStopped: () => {
                    chev.disconnectObject(this);
                    finish();
                },
            });
        };

        if (expanded) {
            // mostra os ícones e espera pela disposição final para saber a
            // distância; até lá ficam invisíveis
            for (const c of items) {
                c.opacity = 0;
                c.show();
            }
            // (já disposto, ainda antes de desenhar: sem saltos)
            const id = global.stage.connect('before-paint', () => {
                global.stage.disconnect(id);
                const dist = this._right.width - chev.width;
                for (const c of items)
                    c.opacity = 255;
                // só se vê o que fica à direita da seta
                run(dist, 0, t => {
                    const edge = t + chev.width;
                    for (const c of items) {
                        const left = Math.min(c.width, Math.max(0, edge - c.x));
                        c.set_clip(left, 0, c.width - left, c.height);
                    }
                });
            });
            global.stage.queue_redraw();
        } else {
            const end = this._right.width;
            const dist = end - chev.width;
            // os ícones acompanham a seta e são cortados no limite da área
            run(0, dist, t => {
                for (const c of items) {
                    c.translation_x = t;
                    const w = Math.min(c.width, Math.max(0, end - (c.x + t)));
                    c.set_clip(0, 0, w, c.height);
                }
            });
        }
    }

    _stopSlide() {
        this._chevron.remove_all_transitions();
        this._chevron.disconnectObject(this);
        for (const c of this._slideItems ?? []) {
            c.translation_x = 0;
            c.opacity = 255;
            c.remove_clip();
        }
        this._chevron.translation_x = 0;
        this._slideItems = null;
        this._sliding = false;
    }

    _pointerInside() {
        const [x, y] = global.get_pointer();
        const [rx, ry] = this._right.get_transformed_position();
        const [px] = this._panel.get_transformed_position();
        return x >= rx && x < px + this._panel.width && y >= ry && y < ry + this._panel.height;
    }

    _menuOpen() {
        return this._items().some(c => (c.get_first_child?.() ?? c).menu?.isOpen);
    }

    // Fundo (TaskbarTray) do início de #panelRight até à direita do painel,
    // composto no tamanho exato (o border-image do St deforma as fatias) num
    // ator próprio por baixo dos ícones; durante a animação a borda segue a seta
    _syncBg() {
        const box = this._right.get_allocation_box();
        const w = Math.round(this._panel.width), h = Math.round(this._panel.height);
        const x = Math.round(box.x1 + this._chevron.translation_x);
        if (!Number.isFinite(x) || w < 44 || h <= 0 || x >= w - 44) {
            this._bg.hide();
            return;
        }
        if (x !== this._bgX || w !== this._bgW || h !== this._bgH) {
            let img;
            try {
                img = slicedImage('tray', w - x, h, [0, 10, 0, 34]);
            } catch (e) {
                console.error(`Zorin XP: área de notificação: ${e}`);
                return;
            }
            this._bgX = x;
            this._bgW = w;
            this._bgH = h;
            this._bg.set_style(`background-image: url("file://${img}"); background-size: auto;`);
        }
        this._bg.show();
        this._bg.allocate(new Clutter.ActorBox({x1: x, y1: 0, x2: w, y2: h}));
    }

    // O botão continua a ser o da zorin-taskbar (é ela que trata o clique);
    // aqui fica sem largura na disposição (não empurra o relógio), sem traço
    // nem ícone, e é posto à mão por cima do canto direito do painel
    _syncDesktop() {
        const b = this._p._showDesktopButton;
        if (!b)
            return;
        if (this._desktop !== b) {
            this._desktop?.disconnectObject(this);
            this._desktop = b;
            const strip = () => {
                if (b.icon?.get_parent() === b)
                    b.remove_child(b.icon);
                if (b.get_style() !== DESKTOP_STYLE)
                    b.set_style(DESKTOP_STYLE);
            };
            // (a zorin-taskbar volta a dispô-lo com largura 0 sempre que
            // reorganiza o painel: repor logo a seguir)
            b.connectObject('notify::style', strip, 'child-added', strip,
                'notify::allocation', () => this._placeDesktop(), this);
            strip();
        }
        this._panel.set_child_above_sibling(b, null);
        this._placeDesktop();
    }

    _placeDesktop() {
        const b = this._desktop;
        const w = Math.round(this._panel.width), h = Math.round(this._panel.height);
        if (!b || w <= DESKTOP_HIT_W || h <= 0)
            return;
        const box = b.get_allocation_box();
        if (box.x1 === w - DESKTOP_HIT_W && box.x2 === w && box.y1 === 0 && box.y2 === h)
            return;
        b.allocate(new Clutter.ActorBox({x1: w - DESKTOP_HIT_W, y1: 0, x2: w, y2: h}));
    }

    destroy() {
        // Cada passo à parte: ao bloquear o ecrã, a zorin-taskbar destrói o
        // botão "Mostrar o ambiente de trabalho" (e outros atores) antes de
        // isto correr; um erro a meio deixava a seta e o fundo no painel, e
        // ao desbloquear vinha outra por cima (seta duplicada)
        const step = fn => {
            try {
                fn();
            } catch (e) {
                console.debug(`Zorin XP: área de notificação: ${e}`);
            }
        };
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        if (this._netTimer)
            GLib.source_remove(this._netTimer);
        this._netTimer = 0;
        this._netIcon = null;
        step(() => this._chevron.destroy());
        step(() => this._bg.destroy());
        if (this._desktop) {
            const desktop = this._desktop;
            this._desktop = null;
            step(() => desktop.disconnectObject(this));
            step(() => desktop.set_style(null));
            step(() => this._p._setShowDesktopButtonStyle?.());
        }
        step(() => this._right.disconnectObject(this));
        step(() => this._p.disconnectObject(this));
        for (const a of this._boxes)
            step(() => a.disconnectObject(this));
        for (const icon of this._appIcons) {
            step(() => {
                icon.disconnectObject(this);
                if (icon._zxpTrayOrig && icon.gicon === icon._zxpColor)
                    icon.gicon = icon._zxpTrayOrig;
                delete icon._zxpColor;
                delete icon._zxpTrayOrig;
            });
        }
        for (const icon of this._icons) {
            step(() => {
                icon.disconnectObject(this);
                if (icon._zxpOrig) {
                    icon.set_style(null);
                    icon.gicon = icon._zxpOrig;
                    delete icon._zxpOrig;
                }
            });
        }
        for (const b of this._watched) {
            step(() => {
                b.disconnectObject(this);
                if (b._zxpStyle !== undefined) {
                    b.set_style(b._zxpStyle);
                    delete b._zxpStyle;
                }
            });
        }
        for (const c of this._touched)
            step(() => c.show());
        this._touched.clear();
        const clock = this._date?._clockDisplay;
        if (clock) {
            step(() => {
                clock.disconnectObject(this);
                clock.text = this._date._clock?.clock ?? clock.text;
            });
        }
        for (const [actor, old] of this._styles.reverse())
            step(() => actor.set_style(old));
        step(() => this._right.set_style(null));
        step(() => this._panel.disconnectObject(this));
        step(() => {
            const style = this._panel.get_style() ?? '';
            if (style.includes('/*zxp*/'))
                this._panel.set_style(style.slice(0, style.indexOf('/*zxp*/')));
        });
    }
}

export class TaskbarTweaks {
    constructor(ext) {
        this._ext = ext;
        this._patches = [];
        this._trays = new Map();
        this._load().catch(e => console.error(`Zorin XP: barra de tarefas: ${e}`));
    }

    async _load() {
        const tb = Main.extensionManager.lookup(TASKBAR_UUID);
        if (!tb)
            return;
        // Mesmo URL que o carregador de extensões usa -> mesmas instâncias dos módulos
        const appIcons = await import(`file://${tb.path}/appIcons.js`);
        const taskbar = await import(`file://${tb.path}/taskbar.js`);
        if (this._destroyed)
            return;

        const AppIcon = appIcons.TaskbarAppIcon;
        const Taskbar = taskbar.Taskbar;

        this._patch(AppIcon.prototype, '_setAppIconPadding', function () {
            this.set_style('padding: 0;');
            this._iconContainer.set_style(ICON_PADDING);
        });
        // Botão da janela ativa "carregado" (xp.css: .focused). Com as janelas
        // desagrupadas a zorin-taskbar só põe .focused no modo agrupado.
        const setIconStyle = AppIcon.prototype._setIconStyle;
        this._patch(AppIcon.prototype, '_setIconStyle', function (isFocused) {
            setIconStyle.call(this, isFocused);
            if (!this._isGroupApps) {
                if (isFocused)
                    this.add_style_class_name('focused');
                else
                    this.remove_style_class_name('focused');
            }
        });
        this._patch(AppIcon.prototype, '_getRunningIndicatorSize', () => 0);
        this._patch(AppIcon.prototype, '_drawRunningIndicator', () => {});
        this._patch(Taskbar.prototype, '_adjustIconSize', function () {
            if (this.iconSize === ICON_SIZE && this._zxpSized)
                return;
            this._zxpSized = true;
            this.iconSize = ICON_SIZE;
            for (const c of this._getTaskbarIcons().concat([this._showAppsIcon]))
                c.child?._delegate?.icon?.setIconSize(ICON_SIZE);
        });
        this._watchTaskbar();
        // ZXP_DEBUG=1 no ambiente do Shell ou ~/.cache/zorin-xp-debug: árvore
        // de atores no diário
        if (GLib.getenv('ZXP_DEBUG') ||
            GLib.file_test(`${GLib.get_user_cache_dir()}/zorin-xp-debug`, GLib.FileTest.EXISTS))
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
                this.dumpPanels();
                return GLib.SOURCE_REMOVE;
            });
    }

    _patch(proto, name, impl) {
        const orig = proto[name];
        if (typeof orig !== 'function')
            return;
        proto[name] = impl;
        this._patches.push([proto, name, orig]);
    }

    // Diagnóstico: árvore de atores do painel no diário (journalctl -o cat | grep ZXP)
    dumpPanels() {
        const walk = (a, d) => {
            if (d > 9 || !a)
                return;
            const cls = a.get_style_class_name?.() ?? '';
            const name = a.get_name?.() ?? '';
            const [w, h] = a.get_size();
            const [x, y] = a.get_transformed_position();
            let box = '';
            const node = a.get_theme_node?.();
            if (node) {
                const pad = [St.Side.TOP, St.Side.RIGHT, St.Side.BOTTOM, St.Side.LEFT].map(sd => node.get_padding(sd));
                box = ` pad=${pad.join(',')} margin=${a.margin_left},${a.margin_right} vis=${a.visible}`;
                if (a._natHPadding !== undefined)
                    box += ` hpad=${a._natHPadding}`;
            }
            console.log(`ZXP ${'  '.repeat(d)}${a.constructor.name}${name ? '#' + name : ''}${cls ? '.' + cls.replace(/ /g, '.') : ''} ` +
                `${Math.round(x)},${Math.round(y)} ${Math.round(w)}x${Math.round(h)}${box} style="${a.get_style?.() ?? ''}"`);
            for (const c of a.get_children())
                walk(c, d + 1);
        };
        for (const p of global.zorinTaskbar?.panels ?? [])
            walk(p, 0);
    }

    // A zorin-taskbar pode ativar-se depois desta extensão (o enable dela é
    // assíncrono) e cria um global.zorinTaskbar novo, e painéis novos, sempre
    // que é (re)ativada: ligar ao objeto atual e acompanhar as mudanças
    _watchTaskbar() {
        const attach = () => {
            const zt = global.zorinTaskbar;
            if (zt && zt !== this._zt) {
                if (this._zt && this._panelsId)
                    this._zt.disconnect(this._panelsId);
                this._zt = zt;
                this._panelsId = zt.connect('panels-created', () => this._refresh());
            }
            this._refresh();
        };
        Main.extensionManager.connectObject('extension-state-changed', (_m, ext) => {
            if (ext?.uuid === TASKBAR_UUID)
                attach();
        }, this);
        attach();
    }

    _addTray(p) {
        if (this._trays.has(p) || !(p._rightBox ?? p.panel?._rightBox))
            return;
        try {
            this._trays.set(p, new XpTray(p));
        } catch (e) {
            console.error(`Zorin XP: área de notificação: ${e}\n${e.stack}`);
        }
    }

    _refresh() {
        // painéis que deixaram de existir (a zorin-taskbar recriou-os)
        const panels = global.zorinTaskbar?.panels ?? [];
        for (const [p, tray] of this._trays) {
            if (!panels.includes(p)) {
                try {
                    tray.destroy();
                } catch (e) {
                    console.debug(`Zorin XP: área de notificação: ${e}`);
                }
                this._trays.delete(p);
            }
        }
        for (const p of panels) {
            if (!this._destroyed && p)
                this._addTray(p);
            const t = p?.taskbar;
            if (!t)
                continue;
            t._zxpSized = false;
            t._adjustIconSize?.();
            for (const c of t._getTaskbarIcons?.() ?? []) {
                const icon = c.child?._delegate;
                icon?._setAppIconPadding?.();
                icon?._displayProperIndicator?.();
            }
        }
    }

    destroy() {
        this._destroyed = true;
        Main.extensionManager.disconnectObject(this);
        if (this._zt && this._panelsId)
            this._zt.disconnect(this._panelsId);
        this._zt = null;
        for (const tray of this._trays.values())
            tray.destroy();
        this._trays.clear();
        for (const [proto, name, orig] of this._patches.reverse())
            proto[name] = orig;
        this._patches = [];
        this._refresh();
    }
}
