/*
 * Theme images for the Shell.
 *
 * St's border-image distorts the bottom and right slices (and ignores
 * shadow lists), so the pieces that must stretch are composed here at their
 * final size and shown as a background at natural size.
 */
import GdkPixbuf from 'gi://GdkPixbuf';
import GLib from 'gi://GLib';

export const XP_DIR = `${GLib.get_home_dir()}/.themes/WindowsXP-Luna/gnome-shell/xp`;
const CACHE_DIR = `${GLib.get_user_cache_dir()}/zorin-xp`;

// 9-slice images already at their final size (St's border-image distorts
// the bottom and right slices): slices [top, right, bottom, left] of the
// theme image, stretched without filtering; optionally with a centred
// glyph. Generated once per session and shown at natural size.
const _sliced = new Map();

// Draws src into dst (w×h) as a 9-slice, stretching without filtering
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
    // (generates it again if the file disappeared, e.g. on a reinstall)
    return _sliced.has(key) && GLib.file_test(_sliced.get(key), GLib.FileTest.EXISTS)
        ? _sliced.get(key) : null;
}

// 9-slice images already at their final size (St's border-image distorts
// the bottom and right slices): slices [top, right, bottom, left] of the
// theme image, stretched without filtering; optionally with a centred
// glyph. Generated once per session and shown at natural size.
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

// Saves a composed image (GdkPixbuf) in the cache and returns the path
export function savedImage(key, pixbuf) {
    const hit = cached(key);
    return hit ?? save(key, pixbuf);
}
