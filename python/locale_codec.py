import locale
import ctypes

_decode_locale = ctypes.pythonapi.PyUnicode_DecodeLocale
_decode_locale.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
_decode_locale.restype = ctypes.py_object

def decode_locale(s, errors=None):
    if errors is not None:
        errors = errors.encode('utf8')
    return _decode_locale(s, errors)

_encode_locale = ctypes.pythonapi.PyUnicode_EncodeLocale
_encode_locale.argtypes = (ctypes.py_object, ctypes.c_char_p)
_encode_locale.restype = ctypes.py_object

def encode_locale(s, errors=None):
    if not isinstance(s, str):
        raise TypeError("first argument type must be str")
    if errors is not None:
        errors = errors.encode('utf8')
    return _encode_locale(s, errors)

for loc in ("C", "POSIX", "fr_FR.ISO8859-1", "fr_FR.UTF-8", "zh_TW.Big5"):
    try:
        locale.setlocale(locale.LC_ALL, loc)
    except locale.Error:
        continue
    for errors in ("strict", "surrogateescape"):
        print("=== %s/%s ===" % (loc, errors))
        print(f"LC_CTYPE locale: {locale.setlocale(locale.LC_CTYPE, None)}")
        if hasattr(locale, "nl_langinfo"):
            print(f"nl_langinfo(CODESET): {locale.nl_langinfo(locale.CODESET)}")
        print()

        for text in (b"\xe9", b"\xff", "\xe9".encode("utf8"), b'\xa2\xdc'):
            try:
                #decoded = _testcapi.decode_locale(text, errors)
                decoded = decode_locale(text, errors)
            except UnicodeError:
                decoded = '<decode error>'
            else:
                decoded = ascii(decoded)
            print("decode %a: %s" % (text, decoded))
        print()

        for text in ("\xe9", "\u20ac", '\uff2e'):
            try:
                #encoded = _testcapi.encode_locale(text, errors)
                encoded = encode_locale(text, errors)
            except UnicodeError:
                encoded = '<encode error>'
            else:
                encoded = ascii(encoded)
            print("encode %a: %s" % (text, encoded))
        print()
