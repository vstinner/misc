"""
Locale tests written for Fedora 29 and Python 3.8:

https://bugs.python.org/issue25812
https://bugs.python.org/issue28604
https://bugs.python.org/issue33954
"""
import codecs
import locale
import os
import re
import sys
import time
import unittest


def get_fedora():
    try:
        fp = open("/etc/fedora-release")
    except OSError:
        return None

    with fp:
        line = fp.readline()

    match = re.match(r"Fedora release ([0-9]+)", line)
    if not match:
        raise Exception("failed to parse Fedora release: %r" % line)

    return int(match.group(1))



PY3 = (sys.version_info >= (3,))
FREEBSD = sys.platform.startswith('freebsd')
MACOS = sys.platform == 'darwin'
BSD = FREEBSD or MACOS
FEBRUARY = time.localtime(time.mktime((2018, 2, 1, 12, 0, 0, 0, 0, 0)))
AUGUST = time.localtime(time.mktime((2018, 8, 1, 12, 0, 0, 0, 0, 0)))
FEDORA = get_fedora()


if not PY3:
    ascii = repr


class Tests(unittest.TestCase):
    def setUp(self):
        self.encoding = None
        self.loc = None

    def tearDown(self):
        self.encoding = None

    def set_locale(self, loc, encoding):
        self.loc = loc
        self.encoding = encoding
        try:
            locale.setlocale(locale.LC_ALL, loc)
        except locale.Error as err:
            self.skipTest("setlocale(LC_ALL, %r) failed: %s" % (loc, err))

        codeset = locale.nl_langinfo(locale.CODESET)
        if codeset:
            try:
                codeset_name = codecs.lookup(codeset).name
            except LookupError:
                raise Exception("nl_langinfo(CODESET)=%r: unknown encoding" % codeset)
            encoding_name = codecs.lookup(encoding).name
            self.assertEqual(codeset_name, encoding_name)

    def assertLocaleEqual(self, value, expected):
        if isinstance(value, bytes):
            text = value.decode(self.encoding)
            self.assertEqual(text, expected,
                             '%s (bytes: %s) != %s; encoding=%s'
                             % (ascii(text), value, ascii(expected), self.encoding))
        else:
            self.assertEqual(value, expected,
                             '%s != %s; encoding=%s'
                             % (ascii(value), ascii(expected), self.encoding))

    def test_fr_FR_iso8859_1(self):
        # Linux, Fedora 27, glibc 2.27
        loc = "fr_FR.ISO8859-1" if BSD else "fr_FR"
        self.set_locale(loc, "ISO-8859-1")
        lc = locale.localeconv()
        if FREEBSD:
            self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
            self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
            self.assertLocaleEqual(os.strerror(2), u'Fichier ou r\xe9pertoire inexistant')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), u'f\xe9vrier')
        self.assertLocaleEqual(time.strftime('%B', AUGUST), u'ao\xfbt')

    def test_fr_FR_utf8(self):
        # Linux, Fedora 27, glibc 2.27
        loc = "fr_FR.UTF-8" if BSD else "fr_FR.utf8"
        self.set_locale(loc, "UTF-8")
        if not MACOS:
            self.assertLocaleEqual(locale.localeconv()['currency_symbol'], u'\u20ac')
        if FREEBSD:
            self.assertLocaleEqual(locale.localeconv()['mon_thousands_sep'], u'\xa0')
            self.assertLocaleEqual(locale.localeconv()['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), u'f\xe9vrier')
        self.assertLocaleEqual(time.strftime('%B', AUGUST), u'ao\xfbt')

    def test_ru_RU(self):
        loc = "ru_RU.ISO8859-5" if BSD else "ru_RU"
        if FEDORA and FEDORA >= 29:
            # Fedora 29, glibc 2.28
            currency_symbol = u'\u0440\u0443\u0431'
            february = '\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
        elif FREEBSD:
            # FreeBSD 11
            currency_symbol = u'\u0440\u0443\u0431.'
            february = u'\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
        elif MACOS:
            # macOS 10.13.2
            currency_symbol = u'\u0440\u0443\u0431.'
            february = u'\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
        else:
            # Linux, Fedora 27, glibc 2.27
            currency_symbol = u'\u0440\u0443\u0431'
            february = u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c'
        self.set_locale(loc, "ISO-8859-5")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], currency_symbol)
        if not MACOS:
            self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
            self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), february)

    def test_ru_RU_koi8r(self):
        loc = "ru_RU.KOI8-R" if BSD else "ru_RU.koi8r"
        if FEDORA and FEDORA >= 29:
            # Fedora 29, glibc 2.28
            currency_symbol = u'\u0440\u0443\u0431'
            february = '\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
        elif BSD:
            # FreeBSD 11.0
            currency_symbol = u'\u0440\u0443\u0431.'
            february = u'\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
        else:
            # Linux, Fedora 27, glibc 2.27
            currency_symbol = u'\u0440\u0443\u0431'
            february = u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c'
        self.set_locale(loc, "KOI8-R")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], currency_symbol)
        if not MACOS:
            self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
            self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY),
                               february)
        if FREEBSD:
            self.assertLocaleEqual(os.strerror(2),
                                   u'\u041d\u0435\u0442 \u0442\u0430\u043a\u043e\u0433\u043e '
                                   u'\u0444\u0430\u0439\u043b\u0430 \u0438\u043b\u0438 '
                                   u'\u043a\u0430\u0442\u0430\u043b\u043e\u0433\u0430')

    def test_ru_RU_utf8(self):
        loc = "ru_RU.UTF-8" if BSD else "ru_RU.utf8"
        if FEDORA and FEDORA >= 29:
            # Fedora 29, glibc 2.28
            currency_symbol = '\u20bd'
            february = '\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
            mon_thousands_sep = '\u202f'
        elif BSD:
            # FreeBSD 11.0
            currency_symbol = u'\u0440\u0443\u0431.'
            february = u'\u0444\u0435\u0432\u0440\u0430\u043b\u044f'
            mon_thousands_sep = u'\xa0'
        else:
            # Linux, Fedora 27, glibc 2.27
            currency_symbol = u'\u20bd'
            february = u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c'
            mon_thousands_sep = u'\xa0'
        thousands_sep = mon_thousands_sep

        self.set_locale(loc, "UTF-8")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], currency_symbol)
        if not MACOS:
            self.assertLocaleEqual(lc['mon_thousands_sep'], mon_thousands_sep)
            self.assertLocaleEqual(lc['thousands_sep'], thousands_sep)
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), february)

    def test_zh_TW_Big5(self):
        loc = "zh_TW.Big5" if BSD else "zh_TW.big5"
        if FREEBSD:
            currency_symbol = u'\uff2e\uff34\uff04'
            decimal_point = u'\uff0e'
            thousands_sep = u'\uff0c'
            date_str = u'\u661f\u671f\u56db 2\u6708'
        else:
            currency_symbol = u'NT$'
            decimal_point = u'.'
            thousands_sep = u','
            if MACOS:
                date_str =  u'\u9031\u56db 2\u6708'
            else:
                date_str = u'\u9031\u56db \u4e8c\u6708'

        self.set_locale(loc, "Big5")

        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], currency_symbol)
        self.assertLocaleEqual(lc['decimal_point'], decimal_point)
        self.assertLocaleEqual(lc['thousands_sep'], thousands_sep)

        self.assertLocaleEqual(time.strftime('%A %B', FEBRUARY),
                               date_str)


class MonetaryTests(unittest.TestCase):
    TESTS = (
        # LC_CTYPE, LC_MONETARY, currency_symbol
        ('en_GB', 'ar_SA.UTF-8', '\u0631.\u0633'),
        ('en_GB', 'fr_FR.UTF-8', '\u20ac'),
        ('en_GB', 'uk_UA.koi8u', '\u0433\u0440\u043d.'),
        ('fr_FR.UTF-8', 'uk_UA.koi8u', '\u0433\u0440\u043d.'),
    )

    def setUp(self):
        # restore all locales at exit
        lc_all = locale.setlocale(locale.LC_ALL, None)
        self.addCleanup(locale.setlocale, locale.LC_ALL, lc_all)

    def test_numeric(self):
        for lc_ctype, lc_monetary, currency_symbol in self.TESTS:
            locale.setlocale(locale.LC_ALL, lc_ctype)
            locale.setlocale(locale.LC_MONETARY, lc_monetary)
            lc = locale.localeconv()
            self.assertEqual(lc['currency_symbol'], currency_symbol)


if __name__ == "__main__":
    unittest.main()
