#!/usr/bin/env python3
# https://haypo-notes.readthedocs.io/cpython.html#embedded-libraries
import re

def grep(filename, pattern):
    regex = re.compile(pattern)
    with open(filename) as fp:
        for line in fp:
            match = regex.search(line)
            if match:
                return match.group(1)
    raise ValueError("unable to find %r in %s" % (pattern, filename))


def dump_version(name, filename, pattern):
    try:
        version = grep(filename, pattern)
    except FileNotFoundError:
        return
    print("%s: %s" % (name, version))

def main():
    dump_version('libffi',
                 'Modules/_ctypes/libffi/configure.ac',
                 r'AC_INIT\([^,]+, \[([^]]+)\],')
    dump_version('libffi_osx',
                 'Modules/_ctypes/libffi_osx/include/fficonfig.h',
                 r'PACKAGE_VERSION "([^"]+)"')
    dump_version('libffi_msvc',
                 'Modules/_ctypes/libffi_msvc/ffi.h',
                 r'libffi (.*) - Copyright \(c\) ')
    filename = 'Modules/expat/expat.h'
    major = grep(filename, r'#define XML_MAJOR_VERSION (.*)')
    minor = grep(filename, r'#define XML_MINOR_VERSION (.*)')
    micro = grep(filename, r'#define XML_MICRO_VERSION (.*)')
    print('expat: %s.%s.%s' % (major, minor, micro))
    dump_version('zlib',
                 'Modules/zlib/zlib.h',
                 r'#define ZLIB_VERSION "(.*)"')
    dump_version('libmpdec',
                 'Modules/_decimal/libmpdec/mpdecimal.h',
                 r'MPD_VERSION "(.*)"')
    dump_version('openssl[Windows]',
                 'PCbuild/get_externals.bat',
                 r'openssl-([0-9].*)')
    dump_version('openssl[macOS]',
                 'Mac/BuildScript/build-installer.py',
                 r'openssl-([0-9][^.]*\.[^.]+\.[^.]+)')
    dump_version('SQLite[Windows]',
                 'PCbuild/get_externals.bat',
                 r'sqlite-([0-9].*)')
    dump_version('SQLite[macOS]',
                 'Mac/BuildScript/build-installer.py',
                 r'SQLite ([0-9][^"]*)')


if __name__ == "__main__":
    main()
