#!/bin/bash
# capture of the test shell: ./shot.sh file.png

D="$(dirname "$(readlink -f "$0")")"
"$D/ev.sh" "(async () => { const {Shell, Gio} = imports.gi; const s = new Shell.Screenshot(); const st = Gio.File.new_for_path('$1').replace(null, false, 0, null); await new Promise((res, rej) => s.screenshot(false, st, (o, r) => { try { o.screenshot_finish(r); res(); } catch (e) { rej(e); } })); st.close(null); return 'ok'; })()"
