"""
Micro-benchmark for the Python operation str.format(). Run it with:

./python.orig benchmark.py script bench_str.py --file=orig
./python.patched benchmark.py script bench_str.py --file=patched
./python.patched benchmark.py compare_to orig patched

Download benchmark.py from:

https://bitbucket.org/haypo/misc/raw/tip/python/benchmark.py
"""


import sys

def run_benchmark(bench):
    use_unicode = sys.version_info >= (3,)
    if use_unicode:
        bmp_lit = '\\u20ac'
        bmp = '"\\u20ac"'
    short_ascii = '"abc"'
    short_int = '123'
    short_float = '12.345'
    short_complex1 = '2j'
    short_complex2 = '1+2j'
    if use_unicode:
        short_bmp = bmp + ' * 3'
        SHORT_ARGS = (short_ascii, short_bmp, short_int)
    else:
        SHORT_ARGS = (short_ascii, short_int)
    SHORT_ARGS += (short_float, short_complex1, short_complex2)

    long_ascii = '"A" * 4096'
    long_int = "2**4096 - 1"
    if use_unicode:
        long_bmp = bmp + ' * 4096'
        LONG_ARGS = (long_ascii, long_bmp, long_int)
    else:
        LONG_ARGS = (long_ascii, long_int)

    huge_ascii = '"A" * (10 * 1024 * 1024)'
    huge_int = "2 ** 123456 - 1"
    if use_unicode:
        huge_bmp = bmp + ' * (10 * 1024 * 1024)'
        HUGE_ARGS = (huge_ascii, huge_bmp, huge_int)
    else:
        HUGE_ARGS = (huge_ascii, huge_int)

    INT_ARGS = (short_int, long_int, huge_int)

    bench.start_group('Basic, short output')
    for arg in SHORT_ARGS:
        bench.timeit(
            setup='fmt="{x}"; x=%s' % arg,
            stmt='fmt.format(x=x)')
        bench.timeit(
            setup='fmt="%%(x)s"; args={"x": %s}' % arg,
            stmt='fmt % args')

    bench.start_group('Basic, long output')
    for arg in LONG_ARGS:
        bench.timeit(
            setup='fmt="{x}"; x=%s' % arg,
            stmt='fmt.format(x=x)')
        bench.timeit(
            setup='fmt="%%(x)s"; args={"x": %s}' % arg,
            stmt='fmt % args')

    bench.start_group('Prefix and suffix, short output')
    for arg in SHORT_ARGS:
        bench.timeit(
            setup='fmt="x={x}."; x=%s' % arg,
            stmt='fmt.format(x=x)')
        bench.timeit(
            setup='fmt="x=%%(x)s."; args={"x": %s}' % arg,
            stmt='fmt % args')

    bench.start_group('Prefix and suffix, long output')
    for arg in LONG_ARGS:
        bench.timeit(
            setup='fmt="x={x}."; x=%s' % arg,
            stmt='fmt.format(x=x)')
        bench.timeit(
            setup='fmt="x=%%(x)s."; args={"x": %s}' % arg,
            stmt='fmt % args')

