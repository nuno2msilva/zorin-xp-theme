#!/usr/bin/env python3
"""Takes Zorin XP's own entries out of a Flatpak override file, leaving the
rest as it was (`flatpak override --unset-env` does not do it: it adds an
"unset" of the variable, which then wins over the global override).

  flatpak_override.py <override file> [--env VAR]... [--fs PATH]...
"""
import argparse
import os

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--fs", action="append", default=[])
    a = ap.parse_args()
    if not os.path.exists(a.file):
        return
    kf = GLib.KeyFile()
    kf.load_from_file(a.file, GLib.KeyFileFlags.KEEP_COMMENTS)

    def has(group, key):
        # (KeyFile.has_key is not available from Python)
        try:
            kf.get_value(group, key)
            return True
        except GLib.Error:
            return False

    def strip_list(group, key, drop):
        if not has(group, key):
            return
        items = [x for x in kf.get_string(group, key).split(";") if x and x not in drop]
        if items:
            kf.set_string(group, key, ";".join(items) + ";")
        else:
            kf.remove_key(group, key)

    for var in a.env:
        if has("Environment", var):
            kf.remove_key("Environment", var)
    strip_list("Context", "unset-environment", set(a.env))
    strip_list("Context", "filesystems", set(a.fs))
    for group in kf.get_groups()[0]:
        if not kf.get_keys(group)[0]:
            kf.remove_group(group)
    kf.save_to_file(a.file)


if __name__ == "__main__":
    main()
