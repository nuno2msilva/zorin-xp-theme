// Zorin XP — autenticação dos ecrãs XP: o verificador do GNOME Shell
// (GdmUtil.ShellUserVerifier: PAM pelo GDM, impressão digital, cartão), sem
// nenhuma interface do GNOME. Sinais:
//   'question' (pergunta, secreta)   o PAM pede algo (normalmente a palavra-passe)
//   'message'  (texto, tipo)         mensagem do PAM (erros, avisos)
//   'failed'   (podeRepetir)         falhou; se podeRepetir, o verificador volta a perguntar
//   'complete'                      autenticação aceite
//   'reset'                         o verificador desistiu/recomeçou (voltar à lista)

import GLib from 'gi://GLib';

import * as Signals from 'resource:///org/gnome/shell/misc/signals.js';
import * as Batch from 'resource:///org/gnome/shell/gdm/batch.js';
import * as GdmUtil from 'resource:///org/gnome/shell/gdm/util.js';

export class XpAuth extends Signals.EventEmitter {
    constructor(gdmClient, reauthenticationOnly) {
        super();
        this._query = null;
        this._preemptive = null;
        this.complete = false;
        this._verifier = new GdmUtil.ShellUserVerifier(gdmClient, {reauthenticationOnly});
        this._verifier.connect('ask-question', (_v, service, question, secret) => {
            this._query = service;
            if (this._preemptive !== null) {
                const answer = this._preemptive;
                this._preemptive = null;
                this._verifier.answerQuery(service, answer);
                return;
            }
            // "Password:" do PAM -> a legenda do XP (o resto como vem)
            this.emit('question', question.replace(/[:：] *$/, '').trim(), secret);
        });
        this._verifier.connect('show-message', (_v, _service, message, type) => {
            if (message)
                this.emit('message', message, type);
        });
        this._verifier.connect('verification-failed', (_v, service, canRetry) => {
            if (this._query === service)
                this._query = null;
            this.emit('failed', canRetry);
        });
        this._verifier.connect('verification-complete', () => {
            this.complete = true;
            this.emit('complete');
        });
        this._verifier.connect('reset', () => {
            this._query = null;
            this.emit('reset');
        });
    }

    begin(userName) {
        this.complete = false;
        this._query = null;
        this._preemptive = null;
        // testes (shell de teste): nunca falar com o GDM/PAM verdadeiros
        if (GLib.getenv('ZXP_LOGON_TEST'))
            return;
        this._verifier.begin(userName, new Batch.Hold());
    }

    answer(text) {
        if (GLib.getenv('ZXP_LOGON_TEST')) {
            this.lastTestAnswer = text;
            return;
        }
        if (this._query) {
            const service = this._query;
            this._query = null;
            this._verifier.answerQuery(service, text);
        } else {
            this._preemptive = text;
        }
    }

    get waiting() {
        return !!this._query;
    }

    cancel() {
        this._query = null;
        this._preemptive = null;
        this._verifier.cancel();
    }

    // espera pelas mensagens pendentes do PAM antes de continuar (como o GNOME)
    finish(onComplete) {
        if (!this._verifier.hasPendingMessages) {
            this._verifier.clear();
            onComplete();
            return;
        }
        const id = this._verifier.connect('no-more-messages', () => {
            this._verifier.disconnect(id);
            this._verifier.clear();
            onComplete();
        });
    }

    destroy() {
        this._verifier.destroy();
        this._verifier = null;
    }
}
