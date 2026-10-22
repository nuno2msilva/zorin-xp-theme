#!/usr/bin/env python3
"""Cliente Marionette mínimo para o Zen de teste (headless, porta 2829).

  mn.py shot <ficheiro.png>      captura da janela inteira (contexto chrome)
  mn.py js '<código>'            corre JS no browser.xhtml e imprime o resultado
  mn.py size <w> <h>             tamanho da janela
  mn.py go <url>                 abre o endereço no separador atual
"""
import base64, json, socket, sys

PORT = 2829


class Marionette:
    def __init__(self, port=PORT):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=60)
        self.id = 0
        self._read()
        # (os alertas das páginas ficam abertos: são o que se quer ver)
        self.cmd("WebDriver:NewSession", {"unhandledPromptBehavior": "ignore"})
        self.cmd("Marionette:SetContext", {"value": "chrome"})

    def _read(self):
        buf = b""
        while b":" not in buf:
            buf += self.s.recv(1)
        n, rest = buf.split(b":", 1)
        n = int(n)
        while len(rest) < n:
            rest += self.s.recv(n - len(rest))
        return json.loads(rest)

    def cmd(self, name, params=None):
        self.id += 1
        msg = json.dumps([0, self.id, name, params or {}]).encode()
        self.s.sendall(str(len(msg)).encode() + b":" + msg)
        while True:
            r = self._read()
            if r[0] == 1 and r[1] == self.id:
                if r[2]:
                    raise RuntimeError(r[2])
                return r[3]

    def js(self, code, args=None):
        return self.cmd("WebDriver:ExecuteScript", {"script": code, "args": args or []}).get("value")


if __name__ == "__main__":
    m = Marionette()
    op = sys.argv[1]
    if op == "shot":
        png = m.cmd("WebDriver:TakeScreenshot", {"full": False})["value"]
        open(sys.argv[2], "wb").write(base64.b64decode(png))
    elif op == "js":
        print(json.dumps(m.js(sys.argv[2]), indent=1, ensure_ascii=False))
    elif op == "size":
        print(m.cmd("WebDriver:SetWindowRect", {"width": int(sys.argv[2]), "height": int(sys.argv[3])}))
    elif op == "go":
        m.js("gBrowser.selectedBrowser.loadURI(Services.io.newURI(arguments[0]), "
             "{triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal()}); return 1", [sys.argv[2]])
