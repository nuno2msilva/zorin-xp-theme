#!/bin/bash
pkill -f "wayland-display=wl-zx[p]"; sleep 1
# (the document portal also mounts doc/ there: with it mounted, the folder stayed)
for d in /tmp/zxp-run.*; do fusermount -u "$d/gvfs" 2>/dev/null; fusermount -u "$d/doc" 2>/dev/null; rm -rf "$d" 2>/dev/null; done
