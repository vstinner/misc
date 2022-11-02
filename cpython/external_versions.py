#!/usr/bin/env python3
# https://pythondev.readthedocs.io/files.html#vendored-external-libraries
import re
import os.path


def grep(filename, pattern):
    regex = re.compile(pattern)
    with open(filename) as fp:
        for line in fp:
            match = regex.search(line)
            if match:
                return match.group(1)
    raise ValueError("unable to find %r in %s" % (pattern, filename))


def get_ensurepip_versions():
    versions = {}
    try:
        names = os.listdir("Lib/ensurepip/_bundled/")
    except OSError:
        return versions

    for name in names:
        name = os.path.basename(name)
        parts = name.split('-')
        name = parts[0]
        if name in ('pip','setuptools'):
            versions[name] = parts[1]

    return versions


def write_version(name, version):
    version = version.strip()
    print("%s: %s" % (name, version))


def grep_version(name, filename, pattern):
    try:
        version = grep(filename, pattern)
    except FileNotFoundError:
        return
    write_version(name, version)

def main():
    grep_version('libffi',
                 'Modules/_ctypes/libffi/configure.ac',
                 r'AC_INIT\([^,]+, \[([^]]+)\],')
    grep_version('libffi_osx',
                 'Modules/_ctypes/libffi_osx/include/fficonfig.h',
                 r'PACKAGE_VERSION "([^"]+)"')
    grep_version('libffi_msvc',
                 'Modules/_ctypes/libffi_msvc/ffi.h',
                 r'libffi (.*) - Copyright \(c\) ')
    filename = 'Modules/expat/expat.h'
    major = grep(filename, r'#define XML_MAJOR_VERSION (.*)')
    minor = grep(filename, r'#define XML_MINOR_VERSION (.*)')
    micro = grep(filename, r'#define XML_MICRO_VERSION (.*)')
    print('expat: %s.%s.%s' % (major, minor, micro))
    grep_version('zlib',
                 'Modules/zlib/zlib.h',
                 r'#define ZLIB_VERSION "(.*)"')
    grep_version('zlib[Windows]',
                 'PCbuild/get_externals.bat',
                 r'zlib-([0-9][^"]*)')
    grep_version('libmpdec',
                 'Modules/_decimal/libmpdec/mpdecimal.h',
                 r'MPD_VERSION "(.*)"')
    grep_version('openssl[Windows]',
                 'PCbuild/get_externals.bat',
                 r'openssl-([0-9].*)')
    grep_version('openssl[macOS]',
                 'Mac/BuildScript/build-installer.py',
                 r'openssl-([0-9][^.]*\.[^.]+\.[^.]+)')
    grep_version('SQLite[Windows]',
                 'PCbuild/get_externals.bat',
                 r'sqlite-([0-9].*)')
    grep_version('SQLite[macOS]',
                 'Mac/BuildScript/build-installer.py',
                 r'SQLite ([0-9][^"]*)')
    grep_version('ncurses[macOS]',
                 'Mac/BuildScript/build-installer.py',
                 r'ftp.gnu.org/pub/gnu/ncurses/ncurses-([0-9]+\.[0-9]+).tar.gz')
    versions = get_ensurepip_versions()
    for name in ('setuptools', 'pip'):
        if name in versions:
            write_version(name, versions[name])


if __name__ == "__main__":
    main()
