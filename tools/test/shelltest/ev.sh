#!/bin/bash
# avalia JS no shell de teste: ./ev.sh 'código'
E=$(cat /tmp/zxp-shelltest.env)
DBUS_SESSION_BUS_ADDRESS=$(cat "$E/bus") gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval "$1"
