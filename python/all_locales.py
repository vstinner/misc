import locale
import _locale
import os
import subprocess
import sys
import time

PY3 = (sys.version_info >= (3,))

if PY3:
    def test_ascii(value):
        value.encode('ascii')
else:
    def test_ascii(value):
        value.decode('ascii')
    ascii = repr

if len(sys.argv) >= 2 and sys.argv[1] == 'current':
    locales = ['']
else:
    proc = subprocess.Popen(['locale', '-a'], stdout=subprocess.PIPE, universal_newlines=True)
    locales = proc.communicate()[0].splitlines()

def test_locale(loc):
    global nonascii

    codeset = _locale.nl_langinfo(_locale.CODESET)
    if loc:
        prefix = loc
    else:
        prefix = _locale.setlocale(locale.LC_CTYPE, None)
    prefix = '%s/%s' % (prefix, codeset)

    lc = locale.localeconv()
    for field, value in sorted(lc.items()):
        if not isinstance(value, str):
            continue
        try:
            test_ascii(value)
        except UnicodeError:
            print("%s: localeconv()['%s'] = %s" % (prefix, field, ascii(value)))
            nonascii += 1

    nerr = 0
    for err in range(1, 150):
        msg = os.strerror(err)
        try:
            test_ascii(msg)
        except UnicodeError:
            print("%s: strerror(%s) = %s" % (prefix, err, ascii(msg)))
            nonascii += 1
            nerr += 1
            if nerr > 3:
                print("%s: (skip next strerror)" % prefix)
                break

    nerr = 0
    fmt = "%A %B %Z"
    for month in range(1, 13):
        t = time.localtime(time.mktime((2018, month, 1, 12, 0, 0, 0, 0, 0)))
        msg = time.strftime(fmt, t)
        try:
            test_ascii(msg)
        except UnicodeError:
            print("%s: strftime(%r) = %s" % (prefix, fmt, ascii(msg)))
            nonascii += 1
            nerr += 1
            if nerr > 3:
                print("%s: (skip next strftime)" % prefix)
                break


invalid_locales = 0
nonascii = 0
for loc in locales:
    try:
        locale.setlocale(locale.LC_ALL, loc)
    except locale.Error:
        invalid_locales += 1
        continue

    try:
        test_locale(loc)
    except Exception as exc:
        raise Exception("Error while testing %s: %s" % (loc, exc))


print("")
if hasattr(sys.flags, 'utf8_mode'):
    print("UTF-8 mode: %s" % sys.flags.utf8_mode)
print("locales: %s" % len(locales))
print("invalid locales: %s" % invalid_locales)
print("non-ASCII: %s" % nonascii)
