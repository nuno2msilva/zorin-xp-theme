/*
 * Imagens do tema para o Shell.
 *
 * O border-image do St deforma as fatias de baixo e da direita (e ignora
 * listas de sombras), por isso as peças que têm de esticar são compostas aqui
 * já no tamanho final e mostradas como fundo no tamanho natural.
 */
import GdkPixbuf from 'gi://GdkPixbuf';
import GLib from 'gi://GLib';

export const XP_DIR = `${GLib.get_home_dir()}/.themes/WindowsXP-Luna/gnome-shell/xp`;
const CACHE_DIR = `${GLib.get_user_cache_dir()}/zorin-xp`;

// Imagens 9-slice já no tamanho final (o border-image do St deforma as
// fatias de baixo e da direita): fatias [cima, direita, baixo, esquerda] da
// imagem do tema, esticadas sem filtragem; opcionalmente com um glifo
// centrado. Geradas uma vez por sessão e mostradas no tamanho natural.
const _sliced = new Map();

// Desenha src em dst (w×h) como 9-slice, esticando sem filtragem
function drawSliced(src, dst, w, h, [t, r, b, l]) {
    const sw = src.get_width(), sh = src.get_height();
    const cols = [[0, l, 0, l], [l, sw - r, l, w - r], [sw - r, sw, w - r, w]];
    const rows = [[0, t, 0, t], [t, sh - b, t, h - b], [sh - b, sh, h - b, h]];
    for (const [sx0, sx1, dx0, dx1] of cols) {
        for (const [sy0, sy1, dy0, dy1] of rows) {
            const sW = sx1 - sx0, sH = sy1 - sy0, dW = dx1 - dx0, dH = dy1 - dy0;
            if (sW <= 0 || sH <= 0 || dW <= 0 || dH <= 0)
                continue;
            const kx = dW / sW, ky = dH / sH;
            src.scale(dst, dx0, dy0, dW, dH, dx0 - sx0 * kx, dy0 - sy0 * ky, kx, ky,
                GdkPixbuf.InterpType.NEAREST);
        }
    }
}

function save(key, pixbuf) {
    GLib.mkdir_with_parents(CACHE_DIR, 0o755);
    const path = `${CACHE_DIR}/${key}.png`;
    pixbuf.savev(path, 'png', [], []);
    _sliced.set(key, path);
    return path;
}

function cached(key) {
    // (volta a gerar se o ficheiro desapareceu, p. ex. numa reinstalação)
    return _sliced.has(key) && GLib.file_test(_sliced.get(key), GLib.FileTest.EXISTS)
        ? _sliced.get(key) : null;
}

// Imagens 9-slice já no tamanho final (o border-image do St deforma as
// fatias de baixo e da direita): fatias [cima, direita, baixo, esquerda] da
// imagem do tema, esticadas sem filtragem; opcionalmente com um glifo
// centrado. Geradas uma vez por sessão e mostradas no tamanho natural.
export function slicedImage(name, w, h, slices, glyph = null) {
    const key = `${name}-${w}x${h}${glyph ? `-${glyph}` : ''}`;
    const hit = cached(key);
    if (hit)
        return hit;
    const src = GdkPixbuf.Pixbuf.new_from_file(`${XP_DIR}/${name}.png`);
    const dst = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, true, 8, w, h);
    dst.fill(0);
    drawSliced(src, dst, w, h, slices);
    if (glyph) {
        const g = GdkPixbuf.Pixbuf.new_from_file(`${XP_DIR}/${glyph}.png`);
        const gw = g.get_width(), gh = g.get_height();
        const gx = Math.floor((w - gw) / 2), gy = Math.floor((h - gh) / 2);
        g.composite(dst, gx, gy, gw, gh, gx, gy, 1, 1, GdkPixbuf.InterpType.NEAREST, 255);
    }
    return save(key, dst);
}

// Grava uma imagem composta (GdkPixbuf) na cache e devolve o caminho
export function savedImage(key, pixbuf) {
    const hit = cached(key);
    return hit ?? save(key, pixbuf);
}
