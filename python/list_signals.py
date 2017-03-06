#!/usr/bin/env python3
import signal

names = [(int(getattr(signal, name)), name)
         for name in dir(signal)
         if name.startswith("SIG") and not name.startswith("SIG_")]
names.sort()
for signum, name in names:
    print("% 2s: %s" % (signum, name))
