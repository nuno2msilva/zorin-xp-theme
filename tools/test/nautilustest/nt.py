#!/usr/bin/env python3
"""Runs Python inside the test Nautilus (zxp_test_hook.py) and shows what
it printed:  nt.py '<code>'   or   nt.py shot <file.png>"""
import os
import sys
import time

RPC = os.path.expanduser('~/.cache/zorin-xp/nautilustest/rpc')
code = sys.argv[1]
if code == 'shot':
    code = f'print(shot({sys.argv[2]!r}))'
out = os.path.join(RPC, 'out.txt')
if os.path.exists(out):
    os.remove(out)
with open(os.path.join(RPC, 'in.tmp'), 'w') as f:
    f.write(code)
os.rename(os.path.join(RPC, 'in.tmp'), os.path.join(RPC, 'in.py'))
for _ in range(int(float(os.environ.get('NT_TIMEOUT', '30')) / 0.05)):
    if os.path.exists(out):
        print(open(out).read(), end='')
        sys.exit(0)
    time.sleep(0.05)
sys.exit('nt.py: sem resposta do Nautilus de teste')
