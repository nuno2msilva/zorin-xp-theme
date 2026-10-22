/*
 * Zorin XP — extensão do GNOME Shell que completa o tema Windows XP Luna
 * onde o CSS não chega:
 *   frames.js  — bordas, ícone e título das janelas com moldura do mutter
 *   taskbar.js — geometria dos botões da zorin-taskbar (ícone 16 px, texto,
 *                sem indicadores) e fundo da área de notificação
 *   startmenu.js — menu Zorin com as faixas e cores do menu Iniciar do XP
 *   prefsRedirect.js — definições da zorin-taskbar como folha de propriedades
 *   menus.js   — menus de contexto do Shell com o aspeto dos menus do XP
 *   logonSound.js — música de arranque / som de início de sessão do XP
 *   xpScreen.js / endSession.js — boas-vindas ao entrar, diálogos Desligar o
 *                computador / Terminar sessão, ecrãs de saída e sons
 *   desktopNames.js — "O meu computador" e "Reciclagem" nos ícones do
 *                ambiente de trabalho
 *   explorerIcons.js — na barra de tarefas, cada janela do Ficheiros com o
 *                ícone da pasta aberta (o clique ao mudar de pasta e o zoom
 *                fixo estão na extensão do próprio Nautilus, src/nautilus-xp)
 *   ieFind.js  — a janela Localizar do IE (Zen) fora da barra de tarefas
 *   zenIcons.js — o IE (Zen) com o favicon da página na legenda e no botão
 *                da barra de tarefas (o ícone vem da extensão src/zen-ie/title)
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
        // de volta depois de bloquear o ecrã / mudar de utilizador: som de logon
        if (this._locked)
            playSound('service-login');
        this._locked = false;
    }

    disable() {
        // bloquear o ecrã (ou mudar de utilizador) desliga as extensões: som de
        // terminar sessão do XP, e o de logon ao voltar
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
