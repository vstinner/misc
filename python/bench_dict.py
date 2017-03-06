"""
Micro-benchmark for the Python operation "key in dict". Run it with:

./python.orig benchmark.py script bench_str.py --file=orig
./python.patched benchmark.py script bench_str.py --file=patched
./python.patched benchmark.py compare_to orig patched

Download benchmark.py from:

https://bitbucket.org/haypo/misc/raw/tip/python/benchmark.py
"""

def try_except(dico, keys):
    for key in keys:
        try:
            value = dico[key]
        except KeyError:
            value = 'default'

def if_key_in(dico, keys):
    for key in keys:
        if key in dico:
            value = dico[key]
        else:
            value = 'default'

def dict_get(dico, keys):
    for key in keys:
        value = dico.get(key, 'default')


def run_benchmark(bench):
    EXISTING_KEYS = ['a', 'b', 'c', 'd', 'xyz'] # note: only strings
    MISSING_KEYS = ['1', 'z', 'q', 'g', 'yyy'] # note: only strings

    dico = dict((key, 'value') for key in EXISTING_KEYS)
    keys = EXISTING_KEYS
    keys = MISSING_KEYS
    keys = EXISTING_KEYS + MISSING_KEYS

    bench.compare_functions(
        ('dict.get', dict_get, dico, keys),
        ('try/except', try_except, dico, keys),
        ('if key in', if_key_in, dico, keys)
    )

if __name__ == "__main__":
    import benchmark
    benchmark.main()
