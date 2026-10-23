// Zorin XP — authentication for the XP screens: GNOME Shell's verifier
// (GdmUtil.ShellUserVerifier: PAM through GDM, fingerprint, smartcard),
// without any GNOME interface. Signals:
//   'question' (question, secret)   PAM asks for something (normally the password)
//   'message'  (text, type)         a PAM message (errors, warnings)
//   'failed'   (canRetry)           failed; if canRetry, the verifier asks again
//   'complete'                      authentication accepted
//   'reset'                         the verifier gave up/started over (back to the list)

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
            // PAM's "Password:" -> XP's label (the rest as it comes)
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
        // tests (test shell): never talk to the real GDM/PAM
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

    // waits for PAM's pending messages before going on (like GNOME)
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
