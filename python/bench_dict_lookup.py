"""
Micro-benchmark for the Python operation "key in dict". Run it with:

./python.orig benchmark.py script bench_str.py --file=orig
./python.patched benchmark.py script bench_str.py --file=patched
./python.patched benchmark.py compare_to orig patched

Download benchmark.py from:

https://bitbucket.org/haypo/misc/raw/tip/python/benchmark.py
"""

"""
Python 2.7.1

keys always exist: try_except=368.7 ms
keys always exist: if_key_in=428.1 ms
keys always exist: dict_get=631.0 ms

keys never exist: try_except=3700.9 ms
keys never exist: if_key_in=337.2 ms
keys never exist: dict_get=640.3 ms

mixed: try_except=4065.6 ms
mixed: if_key_in=764.4 ms
mixed: dict_get=1271.4 ms
"""

import sys
import time

LOOPS = 10**6
EXISTING_KEYS = ['a', 'b', 'c', 'd', 'xyz'] # note: only strings
MISSING_KEYS = ['1', 'z', 'q', 'g', 'yyy'] # note: only strings
dico = dict((key, 'value') for key in EXISTING_KEYS)

def try_except(dico, key):
    for loops in range(LOOPS):
        try:
            value = dico[key]
        except KeyError:
            value = 'default'

def if_key_in(dico, key):
    for loops in range(LOOPS):
        if key in dico:
            value = dico[key]
        else:
            value = 'default'

def dict_get(dico, key):
    for loops in range(LOOPS):
        value = dico.get(key, 'default')

FUNCS = (try_except, if_key_in, dict_get)

def bench(name, dico, keys):
    for func in FUNCS:
        best = None
        for run in range(5):
            before = time.time()
            for key in keys:
                func(dico, key)
            after = time.time()
            dt = after - before
            if best is not None:
                best = min(best, dt)
            else:
                best = dt
        print("%s: %s=%.1f ms" % (name, func.__name__, best * 1000))
    print

print("Python %s.%s.%s" % sys.version_info[:3])
print
bench('keys always exist', dico, EXISTING_KEYS)
bench('keys never exist', dico, MISSING_KEYS)
bench('mixed', dico, EXISTING_KEYS + MISSING_KEYS)
