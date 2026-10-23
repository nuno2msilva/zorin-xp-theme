#!/bin/bash
# virtual click in the test shell: ./click.sh x y
D="$(dirname "$(readlink -f "$0")")"
"$D/q.sh" "const {Clutter, GLib} = imports.gi; const seat = Clutter.get_default_backend().get_default_seat(); globalThis._zxpPtr ??= seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE); const p = globalThis._zxpPtr; const t = GLib.get_monotonic_time(); p.notify_absolute_motion(t, $1, $2); await new Promise(r => setTimeout(r, 120)); p.notify_button(GLib.get_monotonic_time(), Clutter.BUTTON_PRIMARY, Clutter.ButtonState.PRESSED); p.notify_button(GLib.get_monotonic_time()+1000, Clutter.BUTTON_PRIMARY, Clutter.ButtonState.RELEASED); await new Promise(r => setTimeout(r, 300)); return 'sel=' + d?._ui.selected + ' pass=' + d?._ui._pass.visible;"
