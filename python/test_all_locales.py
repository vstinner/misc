import codecs
import locale
import time
import unittest


FEBRUARY = time.localtime(time.mktime((2018, 2, 1, 12, 0, 0, 0, 0, 0)))
AUGUST = time.localtime(time.mktime((2018, 8, 1, 12, 0, 0, 0, 0, 0)))


class Tests(unittest.TestCase):
    def setUp(self):
        self.encoding = None
        self.loc = None

    def tearDown(self):
        self.encoding = None

    def set_locale(self, loc, encoding):
        self.loc = loc
        self.encoding = encoding
        locale.setlocale(locale.LC_ALL, loc)
        codeset = locale.nl_langinfo(locale.CODESET)
        self.assertEqual(codecs.lookup(codeset).name,
                         codecs.lookup(encoding).name)

    def assertLocaleEqual(self, value, expected):
        if isinstance(value, bytes):
            value = value.decode(self.encoding)
        self.assertEqual(value, expected, (value, expected, self.encoding))

    def test_fr_FR_iso88591(self):
        # Linux, Fedora 27, glibc 2.27
        self.set_locale("fr_FR", "ISO-8859-1")
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), u'f\xe9vrier')
        self.assertLocaleEqual(time.strftime('%B', AUGUST), u'ao\xfbt')

    def test_fr_FR_utf8(self):
        # Linux, Fedora 27, glibc 2.27
        self.set_locale("fr_FR.utf8", "UTF-8")
        self.assertLocaleEqual(locale.localeconv()['currency_symbol'], u'\u20ac')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY), u'f\xe9vrier')
        self.assertLocaleEqual(time.strftime('%B', AUGUST), u'ao\xfbt')

    def test_ru_RU(self):
        # Linux, Fedora 27, glibc 2.27
        self.set_locale("ru_RU", "ISO-8859-5")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], u'\u0440\u0443\u0431')
        self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
        self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY),
                               u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c')

    def test_ru_RU_koi8r(self):
        # Linux, Fedora 27, glibc 2.27
        self.set_locale("ru_RU.koi8r", "KOI8-R")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], u'\u0440\u0443\u0431')
        self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
        self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY),
                               u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c')

    def test_ru_RU_utf8(self):
        # Linux, Fedora 27, glibc 2.27
        self.set_locale("ru_RU.utf8", "UTF-8")
        lc = locale.localeconv()
        self.assertLocaleEqual(lc['currency_symbol'], u'\u20bd')
        self.assertLocaleEqual(lc['mon_thousands_sep'], u'\xa0')
        self.assertLocaleEqual(lc['thousands_sep'], u'\xa0')
        self.assertLocaleEqual(time.strftime('%B', FEBRUARY),
                               u'\u0424\u0435\u0432\u0440\u0430\u043b\u044c')


if __name__ == '__main__':
    unittest.main()
