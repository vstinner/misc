"""
Collect informations about Python to help debugging unit test failures.
"""
from __future__ import print_function
import re
import sys


# FIXME: Add boot time, uptime,
# FIXME: CPU mode/frequency/config/temperature?
# FIXME: git branch, tag, version


PYTHON3 = (sys.version_info >= (3, 0))
INT_TYPES = int


def normalize_text(text):
    if text is None:
        return None
    text = str(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class PythonInfo:
    def __init__(self):
        self.info = {}

    def add(self, key, value):
        if key in self.info:
            raise ValueError("duplicate key: %r" % key)

        # accepted types: str, tuple of str, None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return
        elif value is None:
            return
        elif not isinstance(value, INT_TYPES):
            raise TypeError("value type must be str, int or None")

        self.info[key] = value

    def get_infos(self):
        """
        Get informations at a key:value dictionary where values are strings.
        """
        return {key: str(value) for key, value in self.info.items()}


def collect_sys(info_add):
    for attr in (
        'byteorder',
        'executable',
        'flags',
        'maxsize',
        'maxunicode',
        'version',
    ):
        try:
            value = getattr(sys, attr)
        except AttributeError:
            # Example: sys.maxunicode not available on Python 3.3 and newer
            continue
        if attr == 'flags':
            value = str(value)
        info_add('sys.%s' % attr, value)

    encoding = sys.getfilesystemencoding()
    if hasattr(sys, 'getfilesystemencodeerrors'):
        encoding = '%s/%s' % (encoding, sys.getfilesystemencodeerrors())
    info_add('filesystem_encoding', encoding)

    if hasattr(sys, 'hash_info'):
        alg = sys.hash_info.algorithm
        bits = 64 if sys.maxsize > 2**32 else 32
        alg = '%s (%s bits)' % (alg, bits)
        info_add('sys.hash_info', alg)


def collect_platform(info_add):
    import platform

    info_add('platform.python_implementation', platform.python_implementation())
    arch = platform.architecture()
    arch = '%s %s' % (arch[0], arch[1])
    info_add('platform.architecture', arch)
    info_add('platform.platform', platform.platform(aliased=True))


def collect_locale(info_add):
    import locale

    info_add('locale_encoding', locale.getpreferredencoding(False))


def collect_os(info_add):
    import os

    info_add("os.getcwd", os.getcwd())

    if hasattr(os, 'cpu_count'):
        cpu_count = os.cpu_count()
        if cpu_count:
            info_add('os.cpu_count', cpu_count)

    if hasattr(os, 'getloadavg'):
        load = os.getloadavg()
        info_add('os.getloadavg', str(load))


def collect_readline(info_add):
    import readline

    # Python implementations other than CPython may not have
    # these private attributes
    for attr, info_name in (
        ("_READLINE_VERSION", "readline_version"),
        ("_READLINE_RUNTIME_VERSION", "readline_runtime_version"),
        ("_READLINE_LIBRARY_VERSION", "readline_library_version"),
    ):
        try:
            value = getattr(readline, attr)
        except AttributeError:
            # readline._READLINE_LIBRARY_VERSION was added to CPython 3.7
            continue

        if isinstance(value, INT_TYPES):
            value = "%#x" % value
        info_add(info_name, value)


def collect_gdb(info_add):
    import subprocess

    try:
        proc = subprocess.Popen(["gdb", "-nx", "--version"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        if PYTHON3:
            with proc:
                version = proc.communicate()[0]
        else:
            version = proc.communicate()[0]
    except OSError:
        return

    # Only keep the first line
    version = version.splitlines()[0]
    info_add('gdb_version', version)


def collect_tkinter(info_add):
    try:
        import _tkinter
    except ImportError:
        return

    for attr in ('TK_VERSION', 'TCL_VERSION'):
        value = getattr(_tkinter, attr)
        info_add('_tkinter.%s' % attr, value)


def collect_time(info_add):
    import time

    if not hasattr(time, 'get_clock_info'):
        return

    for clock in ('time', 'perf_counter'):
        tinfo = time.get_clock_info(clock)
        info_add('time.%s' % clock, str(tinfo))


def collect_environ(info_add):
    import os

    for name, value in os.environ.items():
        if name.startswith("PYTHON"):
            info_add('os.environ[%s]' % name, value)


def collect_sysconfig(info_add):
    import sysconfig

    for name in (
        'ABIFLAGS',
        'ANDROID_API_LEVEL',
        'CC',
        'CCSHARED',
        'CFLAGS',
        'CFLAGSFORSHARED',
        'PY_LDFLAGS',
        'CONFIG_ARGS',
        'HOST_GNU_TYPE',
        'MACHDEP',
        'MULTIARCH',
        'OPT',
        'PY_CFLAGS',
        'PY_CFLAGS_NODIST',
        'Py_DEBUG',
        'Py_ENABLE_SHARED',
        'SHELL',
        'SOABI',
        'prefix',
    ):
        value = sysconfig.get_config_var(name)
        if name == 'ANDROID_API_LEVEL' and not value:
            # skip ANDROID_API_LEVEL=0
            continue
        value = normalize_text(value)
        info_add('sysconfig[%s]' % name, value)


def collect_ssl(info_add):
    try:
        import ssl
    except ImportError:
        return

    for attr in (
        'OPENSSL_VERSION',
        'OPENSSL_VERSION_INFO',
        'HAS_SNI',
        'OP_ALL',
        'OP_NO_TLSv1_1',
    ):
        try:
            value = getattr(ssl, attr)
        except AttributeError:
            # ssl.OP_NO_TLSv1_1 is not always available
            continue
        if attr.startswith('OP_'):
            value = '%#8x' % value
        else:
            # Convert OPENSSL_VERSION_INFO tuple to str
            value = str(value)
        info_add('ssl.%s' % attr, value)


def collect_socket(info_add):
    import socket

    hostname = socket.gethostname()
    info_add('socket.hostname', hostname)


def collect_info(info):
    error = False
    for collect_func in (
        collect_gdb,
        collect_locale,
        collect_os,
        collect_platform,
        collect_readline,
        collect_sys,
        collect_tkinter,
        collect_time,
        collect_environ,
        collect_sysconfig,
        collect_ssl,
        collect_socket,
    ):
        info_add = info.add
        try:
            collect_func(info_add)
        except Exception as exc:
            print("ERROR: %s() failed: %s" % (collect_func.__name__, exc))
            error = True
            raise

    return error


def dump_infos(infos, file=None):
    infos = sorted(infos.items())
    for key, value in infos:
        value = value.replace("\n", " ")
        print("%s: %s" % (key, value))


def main():
    info = PythonInfo()
    error = collect_info(info)

    infos = info.get_infos()
    dump_infos(infos)

    if error:
        print("Collection failed: exit with error", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
