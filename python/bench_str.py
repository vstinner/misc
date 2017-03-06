"""
Micro-benchmark for the Python operation str.format(). Run it with:

./python.orig benchmark.py script bench_str.py --file=orig
./python.patched benchmark.py script bench_str.py --file=patched
./python.patched benchmark.py compare_to orig patched

Download benchmark.py from:

https://bitbucket.org/haypo/misc/raw/tip/python/benchmark.py
"""
# faster-format
#
# - if the result is just a string, copy the string by reference, don't copy
#   it by value => restore an optimization of the PyAccu API.
#   Examples:
#
#    * "{}".format(str)
#    * "%s".format(str)
#
# - avoid a temporary buffer to format integers (base 2, 8, 10, 16)
#   Examples:
#
#    * "decimal=%s".format(int)
#    * "hex=%x".format(int)
#    * "%o".format(int)
#    * "{}".format(int)
#    * "{:x}".format(int)
#
# - don't overallocate the last argument of a format string.
#   Examples:
#
#    * "x=%s".format("A" * 4096)

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

    bench.start_group('Basic format, short ASCII output')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="{}"; arg=%s' % arg, stmt='fmt.format(arg)')
    bench.timeit(setup='fmt="{:d}"; arg=%s' % short_int, stmt='fmt.format(arg)')
    bench.timeit(setup='fmt="{:x}"; arg=%s' % short_int, stmt='fmt.format(arg)')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="%%s"; arg=%s' % arg, stmt='fmt % arg')
    bench.timeit(setup='fmt="%%d"; arg=%s' % short_int, stmt='fmt % arg')
    bench.timeit(setup='fmt="%%x"; arg=%s' % short_int, stmt='fmt % arg')

    bench.start_group('Basic format, long output')
    for arg in LONG_ARGS:
        bench.timeit(setup='fmt="{}"; arg=%s' % arg, stmt='fmt.format(arg)')
    for arg in LONG_ARGS:
        bench.timeit(setup='fmt="%%s"; arg=%s' % arg, stmt='fmt % arg')
    bench.timeit(setup='fmt="{:d}"; arg=%s' % long_int, stmt='fmt.format(arg)')
    bench.timeit(setup='fmt="{:x}"; arg=%s' % long_int, stmt='fmt.format(arg)')
    bench.timeit(setup='fmt="%%d"; arg=%s' % long_int, stmt='fmt % arg')
    bench.timeit(setup='fmt="%%x"; arg=%s' % long_int, stmt='fmt % arg')

    bench.start_group('Basic format, huge output')
    for arg in HUGE_ARGS:
        bench.timeit(setup='fmt="{}"; arg=%s' % arg, stmt='fmt.format(arg)')
        bench.timeit(setup='fmt="%%s"; arg=%s' % arg, stmt='fmt % arg')

    bench.start_group('One argument with ASCII prefix, short output')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="x={}"; arg=' + arg, stmt='fmt.format(arg)')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="x=%s"; arg=' + arg, stmt='fmt % arg')

    bench.start_group('One argument with ASCII suffix, short output')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="{}:"; arg=' + arg, stmt='fmt.format(arg)')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="%s:"; arg=' + arg, stmt='fmt % arg')

    if use_unicode:
        bench.start_group('One argument with BMP prefix and suffix, short output')
        for arg in SHORT_ARGS:
            bench.timeit(setup='fmt="\\u20ac[{}]"; arg=' + arg, stmt='fmt.format(arg)')
        for arg in SHORT_ARGS:
            bench.timeit(setup='fmt="\\u20ac[%s]"; arg=' + arg, stmt='fmt % arg')

    bench.start_group('Huge output with prefix and suffix')
    for arg in HUGE_ARGS:
        bench.timeit(setup='fmt="{}"; arg=' + arg, stmt='fmt.format(arg)')
        bench.timeit(setup='fmt="%s"; arg=' + arg, stmt='fmt % arg')
        bench.timeit(setup='fmt="x=[{}]"; arg=' + arg, stmt='fmt.format(arg)')
        bench.timeit(setup='fmt="x=[%s]"; arg=' + arg, stmt='fmt % arg')

    bench.start_group('Many short arguments')
    for arg in SHORT_ARGS:
        bench.timeit(setup='fmt="{0}"*1024', stmt='fmt.format(%s)' % arg)
    bench.timeit(setup='fmt="{0}{1}"*1024', stmt='fmt.format(%s, %s)' % (short_ascii, short_int))
    if use_unicode:
        bench.timeit(setup='fmt="{0}{1}{2}"*1024', stmt='fmt.format(%s, %s, %s)' % (short_ascii, short_bmp, short_int))
    bench.timeit(setup='fmt="{0}-"*1024', stmt='fmt.format(%s)' % short_ascii)
    bench.timeit(setup='fmt="{0}-"*1024', stmt='fmt.format(%s)' % short_int)
    bench.timeit(setup='fmt="{0}-{1}="*1024', stmt='fmt.format(%s, %s)' % (short_ascii, short_int))
    if use_unicode:
        bench.timeit(setup='fmt="{0}-{1}={2}#"*1024', stmt='fmt.format(%s, %s, %s)' % (short_ascii, short_bmp, short_int))

    bench.start_group('Many long arguments')
    bench.timeit(
        setup='fmt="{0}"*1024; arg=' + long_ascii,
        stmt='fmt.format(arg)')
    if use_unicode:
        bench.timeit(
            setup='fmt="{0}"*1024; arg=' + long_bmp,
            stmt='fmt.format(arg)')
    bench.timeit(
        setup='fmt="{0}"*1024; arg=' + long_int,
        stmt='fmt.format(arg)')
    bench.timeit(
        setup='fmt="{0}{1}"*1024; args=(%s, %s)' % (long_ascii, long_int),
        stmt='fmt.format(*args)')
    if use_unicode:
        bench.timeit(
            setup='fmt="{0}{1}{2}"*1024; args=(%s, %s, %s)' % (long_ascii, long_bmp, long_int),
            stmt='fmt.format(*args)')
    bench.timeit(
        setup='fmt="{0}-"*1024; arg=' + long_ascii,
        stmt='fmt.format(arg)')
    bench.timeit(
        setup='fmt="{0}-"*1024; arg=' + long_int,
        stmt='fmt.format(arg)')
    bench.timeit(
        setup='fmt="{0}-{1}="*1024; args=(%s, %s)' % (long_ascii, long_int),
        stmt='fmt.format(*args)')
    if use_unicode:
        bench.timeit(
            setup='fmt="{0}-{1}={2}#"*1024; args=(%s, %s, %s)' % (long_ascii, long_bmp, long_int),
            stmt='fmt.format(*args)')

    bench.start_group('Keywords')
    bench.timeit(
        setup='s="The {k1} is {k2} the {k3}."; args={"k1": "x", "k2": "y", "k3": "z"}',
        stmt='s.format(**args)')
    bench.timeit(
        setup='s="The %(k1)s is %(k2)s the %(k3)s."; args={"k1":"x","k2":"y","k3":"z",}',
        stmt='s % args')

    if use_unicode:
        FILL = ('', bmp_lit)
    else:
        FILL = ('',)
    args = SHORT_ARGS
    scm = bench.platform_info.get('scm', '')
    if 'revision=0408001e4765' in scm:
        # Workaround the bug:
        # "{:<10}".format("\u20ac") fails with SystemError("Cannot copy UCS2 characters into a string of ascii characters")
        FILL = ('',)
        args = (short_ascii, short_int)
    for width in (10, 4096):
        bench.start_group('Align to %s characters' % width)
        for fill in FILL:
            for align in ('<', '>', '^'):
                for arg in args:
                    bench.timeit('fmt.format(arg)', 'fmt="{:%s%s%s}"; arg=%s' % (fill, align, width, arg))
        #bench.timeit('fmt.format(arg)', 'fmt="%%-%ss"; arg=%s' % (width, arg))
        #bench.timeit('fmt.format(arg)', 'fmt="%%%ss"; arg=%s' % (width, arg))

    bench.start_group('Format number in the locale')
    for arg in INT_ARGS:
        bench.timeit('fmt.format(arg)', 'fmt="{:,}"; arg=%s;' % arg)

    bench.start_group('str(int)')
    for arg in INT_ARGS:
        bench.timeit(setup='number=' + arg, stmt='str(number)')

