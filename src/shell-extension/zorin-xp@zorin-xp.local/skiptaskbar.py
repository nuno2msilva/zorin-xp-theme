#!/usr/bin/env python3
"""Tira uma janela X11 da barra de tarefas e do Alt+Tab: skiptaskbar.py <xid>

Pede-o ao mutter como as aplicações pedem (a mensagem _NET_WM_STATE com
_NET_WM_STATE_SKIP_TASKBAR e _NET_WM_STATE_SKIP_PAGER), porque o Shell não
tem maneira de o mudar pelo JS. Usado por ieFind.js.
"""
import ctypes
import ctypes.util
import sys


class XClientMessageEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]


class XEvent(ctypes.Union):
    _fields_ = [("xclient", XClientMessageEvent), ("pad", ctypes.c_long * 24)]


CLIENT_MESSAGE = 33
SUBSTRUCTURE_NOTIFY = 1 << 19
SUBSTRUCTURE_REDIRECT = 1 << 20
NET_WM_STATE_ADD = 1
SOURCE_APPLICATION = 1


def main(xid):
    x = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11") or "libX11.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XInternAtom.restype = ctypes.c_ulong
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XDefaultRootWindow.restype = ctypes.c_ulong
    x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.POINTER(XEvent)]
    x.XFlush.argtypes = [ctypes.c_void_p]
    x.XCloseDisplay.argtypes = [ctypes.c_void_p]

    dpy = x.XOpenDisplay(None)
    if not dpy:
        sys.exit("skiptaskbar: sem ligação ao X")
    atom = lambda name: x.XInternAtom(dpy, name, 0)
    ev = XEvent()
    ev.xclient.type = CLIENT_MESSAGE
    ev.xclient.send_event = 1
    ev.xclient.window = xid
    ev.xclient.message_type = atom(b"_NET_WM_STATE")
    ev.xclient.format = 32
    ev.xclient.data[0] = NET_WM_STATE_ADD
    ev.xclient.data[1] = atom(b"_NET_WM_STATE_SKIP_TASKBAR")
    ev.xclient.data[2] = atom(b"_NET_WM_STATE_SKIP_PAGER")
    ev.xclient.data[3] = SOURCE_APPLICATION
    x.XSendEvent(dpy, x.XDefaultRootWindow(dpy), 0, SUBSTRUCTURE_REDIRECT | SUBSTRUCTURE_NOTIFY, ctypes.byref(ev))
    x.XFlush(dpy)
    x.XCloseDisplay(dpy)


if __name__ == "__main__":
    main(int(sys.argv[1], 0))
