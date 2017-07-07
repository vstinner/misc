"""
Collect informations about Python to help debugging unit test failures.
"""


class PythonInfo:
    def __init__(self):
        self.info = {}

    def add(self, key, value):
        if key in self.info:
            raise ValueError("duplicate key: %r" % key)

        if isinstance(value, str):
            value = value.replace("\n", " ")
            value = value.strip()
            if not value:
                return

        if value is None:
            return

        self.info[key] = value

    def get_infos(self):
        """
        Get informations at a key:value dictionary where values are strings.
        """
        return {key: str(value) for key, value in self.info.items()}


def collect_sys(info):
    import sys

    info.add('sys.byteorder', sys.byteorder)
    info.add('sys.flags', sys.flags)
    info.add('sys.maxsize', sys.maxsize)
    info.add('sys.version', sys.version)

    info.add('filesystem_encoding', sys.getfilesystemencoding())
    if hasattr(sys, 'getfilesystemencodeerrors'):
        info.add('filesystem_errors', sys.getfilesystemencodeerrors())

    if hasattr(sys, 'hash_info'):
        alg = (sys.hash_info.algorithm,
               "64bit" if sys.maxsize > 2**32 else "32bit")
        info.add('hash algorithm', alg)


def collect_platform(info):
    import platform

    info.add('python_implementation', platform.python_implementation())
    info.add('platform', platform.platform(aliased=True))


def collect_locale(info):
    import locale

    info.add('locale_encoding', locale.getpreferredencoding(False))


def collect_os(info):
    import os

    info.add("cwd", os.getcwd())
    if hasattr(os, 'cpu_count'):
        cpu_count = os.cpu_count()
        if cpu_count:
            info.add('cpu_count', cpu_count)


def collect_readline(info):
    import readline

    # Python implementations other than CPython may not have
    # these private attributes
    if hasattr(readline, "_READLINE_VERSION"):
        info.add("readline_version", "%#x" %
                 readline._READLINE_VERSION)
        info.add("readline_runtime_version",
                 "%#x" % readline._READLINE_RUNTIME_VERSION)
    if hasattr(readline, "_READLINE_LIBRARY_VERSION"):
        info.add("readline_library_version",
                 readline._READLINE_LIBRARY_VERSION)


def collect_gdb(info):
    import subprocess
    import sys

    try:
        proc = subprocess.Popen(["gdb", "-nx", "--version"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        with proc:
            version = proc.communicate()[0]
    except OSError:
        return

    # Only keep the first line
    version = version.splitlines()[0]
    info.add('gdb_version', version)


def collect_tkinter(info):
    try:
        import _tkinter
    except ImportError:
        return

    info.add('tcl_version', _tkinter.TCL_VERSION)


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
    ):
        try:
            collect_func(info)
        except Exception as exc:
            print("%s failed: %s" % (collect_func, exc))
            error = True

    return error


def dump_infos(infos, file=None):
    infos = sorted(infos.items())
    for key, value in infos:
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
