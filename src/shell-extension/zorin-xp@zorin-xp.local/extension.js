/*
 * Zorin XP — GNOME Shell extension that completes the Windows XP Luna theme
 * where CSS cannot reach:
 *   frames.js  — borders, icon and title of windows with a mutter frame
 *   taskbar.js — geometry of the zorin-taskbar buttons (16 px icon, text,
 *                no indicators) and the notification area background
 *   startmenu.js — Zorin menu with the bands and colours of XP's Start menu
 *   prefsRedirect.js — zorin-taskbar settings as a property sheet
 *   menus.js   — the Shell's context menus with the look of XP's menus
 *   logonSound.js — XP's startup music / logon sound
 *   xpScreen.js / endSession.js — welcome when logging on, the Turn Off
 *                Computer / Log Off dialogs, exit screens and sounds
 *   desktopNames.js — "O meu computador" and "Reciclagem" on the desktop
 *                icons
 *   explorerIcons.js — on the taskbar, each Files window with the icon of
 *                the open folder (the click when changing folders and the
 *                fixed zoom are in Nautilus's own extension, src/nautilus-xp)
 *   ieFind.js  — IE's (Zen's) Find window off the taskbar
 *   zenIcons.js — IE (Zen) with the page's favicon in the caption and on the
 *                taskbar button (the icon comes from the src/zen-ie/title extension)
 */
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {Frames} from './frames.js';
import {TaskbarTweaks} from './taskbar.js';
import {StartMenuTweaks} from './startmenu.js';
import {PrefsRedirect} from './prefsRedirect.js';
import {MenuTweaks} from './menus.js';
import {playLogonSound} from './logonSound.js';
import {sessionWelcome} from './xpScreen.js';
import {EndSession, playSound} from './endSession.js';
import {DesktopNames} from './desktopNames.js';
import {ExplorerIcons} from './explorerIcons.js';
import {ZenIcons} from './zenIcons.js';
import {IeFind} from './ieFind.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class ZorinXpExtension extends Extension {
    enable() {
        this._frames = new Frames(this);
        this._taskbar = new TaskbarTweaks(this);
        this._startmenu = new StartMenuTweaks(this);
        this._prefs = new PrefsRedirect();
        this._menus = new MenuTweaks();
        this._welcome = sessionWelcome(this.path);
        playLogonSound();
        this._endSession = new EndSession(this);
        this._desktopNames = new DesktopNames();
        this._explorerIcons = new ExplorerIcons();
        this._zenIcons = new ZenIcons(this);
        this._ieFind = new IeFind(this.path);
        // back after locking the screen / switching user: logon sound
        if (this._locked)
            playSound('service-login');
        this._locked = false;
    }

    disable() {
        // locking the screen (or switching user) disables the extensions: XP's
        // log off sound, and the logon one when coming back
        if (Main.sessionMode.isLocked) {
            playSound('service-logout');
            this._locked = true;
        }
        this._ieFind?.destroy();
        this._ieFind = null;
        this._zenIcons?.destroy();
        this._zenIcons = null;
        this._explorerIcons?.destroy();
        this._explorerIcons = null;
        this._desktopNames?.destroy(Main.sessionMode.isLocked);
        this._desktopNames = null;
        this._endSession?.destroy();
        this._endSession = null;
        this._welcome?.destroy();
        this._welcome = null;
        this._menus?.destroy();
        this._menus = null;
        this._prefs?.destroy();
        this._prefs = null;
        this._startmenu?.destroy();
        this._startmenu = null;
        this._taskbar?.destroy();
        this._taskbar = null;
        this._frames?.destroy();
        this._frames = null;
    }
}
