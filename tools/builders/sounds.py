"""freedesktop sound theme from XP's "Windows Default" scheme.

XP's event mapping comes from inf/mmopt.inf (HKCU\\AppEvents\\Schemes,
.Current values). Each freedesktop event is tied to the equivalent XP
event; events that were silent in XP get an empty WAV so they do not fall
back to the fallback theme (freedesktop).
"""
import os
import shutil
import struct

from lib import assets

# XP event (AppEvents) -> file in Windows/Media (from mmopt.inf)
XP_SCHEME = {
    ".Default": "Windows XP Ding.wav",
    "SystemAsterisk": "Windows XP Error.wav",
    "SystemExclamation": "Windows XP Exclamation.wav",
    "SystemHand": "Windows XP Critical Stop.wav",
    "SystemQuestion": None,
    "SystemNotification": "Windows XP Balloon.wav",
    "SystemStart": "Windows XP Startup.wav",
    "SystemExit": "Windows XP Shutdown.wav",
    "WindowsLogon": "Windows XP Logon Sound.wav",
    "WindowsLogoff": "Windows XP Logoff Sound.wav",
    "DeviceConnect": "Windows XP Hardware Insert.wav",
    "DeviceDisconnect": "Windows XP Hardware Remove.wav",
    "DeviceFail": "Windows XP Hardware Fail.wav",
    "LowBatteryAlarm": "Windows XP Battery Low.wav",
    "CriticalBatteryAlarm": "Windows XP Battery Critical.wav",
    "MailBeep": "Windows XP Notify.wav",
    "PrintComplete": "Windows XP Print complete.wav",
    "EmptyRecycleBin": "Windows XP Recycle.wav",
    "Minimize": None,
    "Maximize": None,
    "RestoreUp": None,
    "RestoreDown": None,
    "Open": None,
    "Close": None,
    # Internet Explorer / Explorer (Explorer events; SP2 adds the last two in
    # system32/ieuinit.inf). "Iniciar navegação" (Start Navigation): the click
    # when a page or a folder opens.
    "Navigating": "Windows XP Start.wav",
    "ActivatingDocument": None,
    "BlockedPopup": "Windows XP Pop-up Blocked.wav",
    "SecurityBand": "Windows XP Information Bar.wav",
}

# Nome freedesktop (Sound Naming Spec) -> evento XP
FREEDESKTOP = {
    "bell": ".Default",
    "bell-terminal": ".Default",
    "bell-window-system": ".Default",
    "audio-volume-change": ".Default",      # XP's volume control played the "Ding"
    "dialog-information": "SystemAsterisk",
    "dialog-warning": "SystemExclamation",
    "dialog-error": "SystemHand",
    "dialog-question": "SystemQuestion",
    "message": "SystemNotification",
    "message-new-instant": "SystemNotification",
    "message-new-email": "MailBeep",
    "desktop-login": "SystemStart",           # first logon after boot: the startup music; later ones: service-login (logonSound.js)
    "desktop-logout": "WindowsLogoff",
    "service-login": "WindowsLogon",
    "service-logout": "WindowsLogoff",
    "system-bootup": "SystemStart",
    "system-shutdown": "SystemExit",
    "device-added": "DeviceConnect",
    "device-removed": "DeviceDisconnect",
    "device-failed": "DeviceFail",
    "battery-low": "LowBatteryAlarm",
    "battery-caution": "CriticalBatteryAlarm",
    "suspend-error": "DeviceFail",
    "trash-empty": "EmptyRecycleBin",
    "complete": "PrintComplete",
    "window-minimized": "Minimize",
    "window-maximized": "Maximize",
    "window-unmaximized": "RestoreDown",
    "window-new": "Open",
    "window-close": "Close",
    # No XP equivalent: explicit silence
    "power-plug": None,
    "power-unplug": None,
    "network-connectivity-established": None,
    "network-connectivity-lost": None,
    "screen-capture": None,
    "camera-shutter": None,
    "theme-demo": "SystemStart",
}


def silent_wav(path, rate=22050):
    """Valid PCM WAV with 10 ms of silence."""
    frames = rate // 100
    data = b"\0\0" * frames
    hdr = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(data), b"WAVE", b"fmt ", 16,
                      1, 1, rate, rate * 2, 2, 16, b"data", len(data))
    with open(path, "wb") as f:
        f.write(hdr + data)


def build(out_dir, name="WindowsXP"):
    """Sound theme in out_dir/<name>, with the sounds from assets/sounds."""
    theme = os.path.join(out_dir, name)
    stereo = os.path.join(theme, "stereo")
    os.makedirs(stereo, exist_ok=True)
    with open(os.path.join(theme, "index.theme"), "w") as f:
        f.write(f"[Sound Theme]\nName=Windows XP\nComment=Esquema de sons predefinido do Windows XP\n"
                f"Inherits=freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n")
    silent = os.path.join(stereo, "_silent.wav")
    silent_wav(silent)
    for fd_name, event in FREEDESKTOP.items():
        wav = XP_SCHEME.get(event) if event else None
        dst = os.path.join(stereo, fd_name + ".wav")
        if wav:
            shutil.copyfile(assets.sound(wav), dst)
        else:
            os.symlink("_silent.wav", dst)
    # Extra sounds (not tied to events) used by the shell/autostart
    extras = os.path.join(theme, "xp")
    os.makedirs(extras, exist_ok=True)
    for wav in ("Windows XP Logon Sound.wav", "Windows XP Startup.wav",
                "Windows XP Logoff Sound.wav", "Windows XP Shutdown.wav",
                # (navigation: Files and Zen play them separately)
                "Windows XP Start.wav", "Windows XP Pop-up Blocked.wav",
                "Windows XP Information Bar.wav",
                # (sending to the Recycle Bin: Files and the "Save As" dialog)
                "Windows XP Recycle.wav"):
        shutil.copyfile(assets.sound(wav), os.path.join(extras, wav))
    return theme
