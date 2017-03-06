#!/usr/bin/env python
import codecs
import locale
import os
import sys

def normalize_encoding(encoding):
    return codecs.lookup(encoding).name

locale_encoding = locale.getpreferredencoding()
locale_encoding = normalize_encoding(locale_encoding)
if sys.platform == 'win32':
    try:
        import ctypes
    except ImportError:
        ansi_code_page = locale_encoding
        oem_code_page = None
        console_code_page = sys.stdin.encoding
        console_output_code_page = sys.stdout.encoding
    else:
        ansi_code_page = ctypes.windll.kernel32.GetACP()
        oem_code_page = ctypes.windll.kernel32.GetOEMCP()
        console_code_page = ctypes.windll.kernel32.GetConsoleCP()
        console_output_code_page = ctypes.windll.kernel32.GetConsoleOutputCP()

    fs_encoding = ansi_code_page
    fs_errors = 'strict'
    print("Filesystem encoding: %s/%s" % (fs_encoding, fs_errors))

    print("Windows ANSI code page: %s" % ansi_code_page)
    if oem_code_page:
        print("Windows OEM code page: %s" % oem_code_page)
    if console_code_page != console_output_code_page:
        print("Windows Console input encoding: %s" % console_code_page)
        print("Windows Console output encoding: %s" % console_output_code_page)
    else:
        print("Windows Console encoding: %s" % console_output_code_page)
else:
    fs_encoding = sys.getfilesystemencoding()
    fs_encoding = normalize_encoding(fs_encoding)
    if sys.version_info >= (3,):
        fs_errors = 'surrogateescape'
    else:
        fs_errors = 'strict'

    print("Locale encoding: %s" % locale_encoding)
    print("Filesystem encoding: %s/%s" % (fs_encoding, fs_errors))
    current_locale = locale.setlocale(locale.LC_ALL, '')
    print('setlocale(LC_ALL, "") -> %s' % (current_locale,))

    for name in ('LANG', 'LC_ALL', 'LC_CTYPE'):
        if name in os.environ:
            value = repr(os.environ[name])
        else:
            value = '<unset>'
        print("$%s: %s" % (name, value))

