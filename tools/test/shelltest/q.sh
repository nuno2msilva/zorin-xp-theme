#!/bin/bash
# avalia JS com Main disponível: ./q.sh 'return Main.foo'
D="$(dirname "$(readlink -f "$0")")"
"$D/ev.sh" "(async () => { const Main = await import('resource:///org/gnome/shell/ui/main.js'); const d = Main.screenShield._dialog; $1 })()"
