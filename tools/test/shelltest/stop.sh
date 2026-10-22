#!/bin/bash
pkill -f "wayland-display=wl-zx[p]"; sleep 1
for d in /tmp/zxp-run.*; do fusermount -u "$d/gvfs" 2>/dev/null; rm -rf "$d" 2>/dev/null; done
