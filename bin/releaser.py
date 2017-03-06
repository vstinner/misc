#!/usr/bin/env python3
"""
Script to upload 32 bits and 64 bits wheel packages for Python 3.3 on Windows.

Usage: "python release.py HG_TAG" where HG_TAG is a Mercurial tag, usually
a version number like "3.4.2".

Requirements:

- Python 3.3 and newer requires the Windows SDK 7.1 to build wheel packages
- Python 2.7 requires the Windows SDK 7.0
- the aiotest module is required to run aiotest tests

Configuration file:

    [project]
    name = trollius
    debug_env_var = TROLLIUSDEBUG
    python_versions = 2.7, 3.3, 3.4
"""
import contextlib
import optparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


PY3 = (sys.version_info >= (3,))
HG = 'hg'
GIT = 'git'
SDK_ROOT = r"C:\Program Files\Microsoft SDKs\Windows"
BATCH_FAIL_ON_ERROR = "@IF %errorlevel% neq 0 exit /b %errorlevel%"
WINDOWS = (sys.platform == 'win32')


def parse_python_version(text):
    return tuple(map(int, text.strip().split('.')))


def get_architecture_bits():
    arch = platform.architecture()[0]
    return int(arch[:2])


class PythonVersion:
    def __init__(self, version_info, bits):
        if len(version_info) not in (1, 2):
            raise ValueError("unsupported version info: %s" % (version_info,))
        self.version_info = version_info
        self.version = ''.join(map(str, version_info))
        self.bits = bits
        self._executable = None

    @staticmethod
    def running():
        bits = get_architecture_bits()
        pyver = PythonVersion(sys.version_info[:2], bits)
        pyver._executable = sys.executable
        return pyver

    def _get_executable_windows(self, app):
        if self.bits == 32:
            executable = 'c:\\Python%s%s_32bit\\python.exe'
        else:
            executable = 'c:\\Python%s%s\\python.exe'
        if len(self.version_info) != 2:
            raise Exception("unable to find executable for %s" % self)
        major, minor = self.version_info
        executable = executable % (self.major, self.minor)
        if not os.path.exists(executable):
            print("Unable to find python %s" % self)
            print("%s does not exists" % executable)
            sys.exit(1)
        return executable

    def _get_executable_unix(self, app):
        executable = 'python%s' % self.version
        if hasattr(shutil, 'which'):
            executable = shutil.which(executable)
        return executable

    def get_executable(self, app):
        if self._executable:
            return self._executable

        if WINDOWS:
            executable = self._get_executable_windows(app)
        else:
            executable = self._get_executable_unix(app)
        if not executable:
            print("Unable to find executable of %s" % self)
            sys.exit(1)

        if len(self.version_info) == 1:
            format_version = '{ver[0]}'
        else:
            format_version = '{ver[0]}.{ver[1]}'
        code = (
            'import platform, sys; '
            'print("%s {bits}".format('
            'ver=sys.version_info, '
            'bits=platform.architecture()[0]))'
        ) % format_version
        try:
            exitcode, stdout = app.get_output(executable, '-c', code,
                                              ignore_stderr=True)
        except OSError as exc:
            print("Error while checking %s:" % self)
            print(str(exc))
            print("Executable: %s" % executable)
            sys.exit(1)
        else:
            stdout = stdout.rstrip()
            expected = "%s %sbit" % (self.version, self.bits)
            if stdout != expected:
                print("Python version or architecture doesn't match")
                print("got %r, expected %r" % (stdout, expected))
                print("Executable: %s" % executable)
                sys.exit(1)

        self._executable = executable
        return executable

    def __str__(self):
        return 'Python %s (%s bits)' % (self.version, self.bits)


class SCM:
    NAME = 'scm'

    def __init__(self, app):
        self.app = app

    def get_local_changes(self):
        pass

    def checkout(self, revision):
        pass

    def get_revision(self):
        pass


class Mercurial(SCM):
    NAME = 'Mercurial'

    def get_local_changes(self):
        status = self.app.check_output(HG, 'status')
        return [line for line in status.splitlines()
                if not line.startswith("?")]

    def checkout(self, revision):
        self.app.check_output(HG, 'update', revision)

    def get_revision(self):
        return self.app.check_output(HG, 'id').rstrip()


class Git(SCM):
    NAME = 'Git'

    def get_local_changes(self):
        status = self.app.check_output(GIT, 'status', '--porcelain')
        return [line for line in status.splitlines()
                if not line.startswith("?")]

    def checkout(self, revision):
        self.app.check_output(GIT, 'checkout', revision)

    def get_revision(self):
        return self.app.check_output(GIT, 'rev-parse', 'HEAD').rstrip()



class Releaser(object):
    def __init__(self):
        root = os.getcwd()
        self.root = os.path.realpath(root)

        self.parse_config()

        if os.path.exists(os.path.join(self.root, '.hg')):
            self.scm = Mercurial(self)
        else:
            self.scm = Git(self)

        # Set these attributes to True to run also register sdist upload
        self.wheel = False
        self.test = False
        self.test_doc = False
        self.register = False
        self.sdist = False
        self.aiotest = False
        self.verbose = False
        self.upload = False
        # Release mode: enable more tests
        self.release = False
        if WINDOWS:
            supported_archs = (32, 64)
        else:
            bits = get_architecture_bits()
            supported_archs = (bits,)

        versions = self.python_versions
        self.python_versions = []
        for version in versions:
            for bits in supported_archs:
                pyver = PythonVersion(version, bits)
                self.python_versions.append(pyver)

    def parse_config(self):
        cfg = configparser.RawConfigParser()
        cfg.read("releaser.conf")
        self.project = cfg.get('project', 'name')
        try:
            self.debug_env_var = cfg.get('project', 'debug_env_var')
        except configparser.NoOptionError:
            self.debug_env_var = None
        versions = cfg.get('project', 'python_versions')

        self.python_versions = [parse_python_version(version)
                                for version in versions.split(",")]

    @contextlib.contextmanager
    def _popen(self, args, **kw):
        verbose = kw.pop('verbose', True)
        if self.verbose and verbose:
            print('+ ' + ' '.join(args))
        if PY3:
            kw['universal_newlines'] = True
        proc = subprocess.Popen(args, **kw)
        try:
            yield proc
        except:
            proc.kill()
            proc.wait()
            raise

    def get_output(self, *args, **kw):
        kw['stdout'] = subprocess.PIPE
        ignore_stderr = kw.pop('ignore_stderr', False)
        if ignore_stderr:
            devnull = open(os.path.devnull, 'wb')
            kw['stderr'] = devnull
        else:
            kw['stderr'] = subprocess.STDOUT
        try:
            with self._popen(args, **kw) as proc:
                stdout, stderr = proc.communicate()
                return proc.returncode, stdout
        finally:
            if ignore_stderr:
                devnull.close()

    def check_output(self, *args, **kw):
        exitcode, output = self.get_output(*args, **kw)
        if exitcode:
            sys.stdout.write(output)
            sys.stdout.flush()
            sys.exit(1)
        return output

    def run_command(self, *args, **kw):
        with self._popen(args, **kw) as proc:
            exitcode = proc.wait()
        if exitcode:
            sys.exit(exitcode)

    def remove_directory(self, name):
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            if self.verbose:
                print("Remove directory: %s" % name)
            shutil.rmtree(path)

    def remove_file(self, name):
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            if self.verbose:
                print("Remove file: %s" % name)
            os.unlink(path)

    def windows_sdk_setenv(self, pyver):
        if pyver.version_info >= (3, 3):
            path = "v7.1"
            sdkver = (7, 1)
        else:
            path = "v7.0"
            sdkver = (7, 0)
        setenv = os.path.join(SDK_ROOT, path, 'Bin', 'SetEnv.cmd')
        if not os.path.exists(setenv):
            print("Unable to find Windows SDK %s.%s for %s"
                  % (sdkver[0], sdkver[1], pyver))
            print("Please download and install it")
            print("%s does not exists" % setenv)
            sys.exit(1)
        if pyver.bits == 64:
            arch = '/x64'
        else:
            arch = '/x86'
        cmd = ["CALL", setenv, "/release", arch]
        return (cmd, sdkver)

    def quote(self, arg):
        if not re.search("[ '\"]", arg):
            return arg
        # FIXME: should we escape "?
        return '"%s"' % arg

    def quote_args(self, args):
        return ' '.join(self.quote(arg) for arg in args)

    def cleanup(self):
        if self.verbose:
            print("Cleanup")
        self.remove_directory('build')
        self.remove_directory('dist')
        self.remove_directory(self.project + '.egg-info')
        self.remove_directory('.tox')
        self.remove_file('_overlapped.pyd')
        self.remove_file(os.path.join(self.project, '_overlapped.pyd'))

    def sdist_upload(self):
        self.cleanup()
        self.run_command(sys.executable, 'setup.py', 'sdist', 'upload')

    def build_inplace(self, pyver):
        print("Build for %s" % pyver)
        self.build(pyver, 'build')

        if WINDOWS:
            if pyver.bits == 64:
                arch = 'win-amd64'
            else:
                arch = 'win32'
            build_dir = 'lib.%s-%s' % (arch, pyver.version)
            src = os.path.join(self.root, 'build', build_dir,
                               self.project, '_overlapped.pyd')
            dst = os.path.join(self.root, self.project, '_overlapped.pyd')
            shutil.copyfile(src, dst)

    def runtests(self, pyver):
        print("Run tests on %s" % pyver)

        if WINDOWS and not self.options.no_compile:
            self.build_inplace(pyver)

        release_env = dict(os.environ)
        if self.debug_env_var:
            release_env.pop(self.debug_env_var, None)

        dbg_env = dict(os.environ)
        if self.debug_env_var:
            dbg_env[self.debug_env_var] = '1'

        python = pyver.get_executable(self)
        args = (python, 'runtests.py', '-r')

        if self.release:
            print("Run runtests.py in release mode on %s" % pyver)
            self.run_command(*args, env=release_env)

        print("Run runtests.py in debug mode on %s" % pyver)
        self.run_command(*args, env=dbg_env)

        if self.aiotest:
            args = (python, 'run_aiotest.py')

            if self.release:
                print("Run aiotest in release mode on %s" % pyver)
                self.run_command(*args, env=release_env)

            print("Run aiotest in debug mode on %s" % pyver)
            self.run_command(*args, env=dbg_env)
        print("")

    def check_doc(self):
        filename = 'README.rst'
        if os.path.exists(filename):
            with tempfile.NamedTemporaryFile() as tmp:
                self.run_command('rst2html', filename, tmp.name)

    def run_all_tests(self):
        if os.path.exists('tox.ini'):
            self.run_command('tox')
        else:
            for pyver in self.python_versions:
                self.runtests(pyver)

        self.check_doc()

    def _build_windows(self, pyver, cmd):
        setenv, sdkver = self.windows_sdk_setenv(pyver)

        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".bat",
                                           delete=False)
        with temp:
            temp.write("SETLOCAL EnableDelayedExpansion\n")
            temp.write(self.quote_args(setenv) + "\n")
            temp.write(BATCH_FAIL_ON_ERROR + "\n")
            # Restore console colors: lightgrey on black
            temp.write("COLOR 07\n")
            temp.write("\n")
            temp.write("SET DISTUTILS_USE_SDK=1\n")
            temp.write("SET MSSDK=1\n")
            temp.write("CD %s\n" % self.quote(self.root))
            temp.write(self.quote_args(cmd) + "\n")
            temp.write(BATCH_FAIL_ON_ERROR + "\n")

        try:
            if self.verbose:
                print("Setup Windows SDK %s.%s" % sdkver)
                print("+ " + ' '.join(cmd))
            # SDK 7.1 uses the COLOR command which makes SetEnv.cmd failing
            # if the stdout is not a TTY (if we redirect stdout into a file)
            if self.verbose or sdkver >= (7, 1):
                self.run_command(temp.name, verbose=False)
            else:
                self.check_output(temp.name, verbose=False)
        finally:
            os.unlink(temp.name)

    def _build_unix(self, pyver, cmd):
        self.check_output(*cmd)

    def build(self, pyver, *cmds):
        self.cleanup()

        python = pyver.get_executable(self)
        cmd = [python, 'setup.py'] + list(cmds)

        if WINDOWS:
            self._build_windows(pyver, cmd)
        else:
            self._build_unix(pyver, cmd)

    def test_wheel(self, pyver):
        print("Test building wheel package for %s" % pyver)
        self.build(pyver, 'bdist_wheel')

    def publish_wheel(self, pyver):
        print("Build and publish wheel package for %s" % pyver)
        self.build(pyver, 'bdist_wheel', 'upload')

    def parse_options(self):
        parser = optparse.OptionParser(
            description="Run all unittests.",
            usage="%prog [options] command")
        parser.add_option(
            '-v', '--verbose', action="store_true", dest='verbose',
            default=0, help='verbose')
        parser.add_option(
            '-t', '--tag', type="str",
            help='SCM tag or revision, required to release')
        parser.add_option(
            '-p', '--python', type="str",
            help='Only build/test one specific Python version, ex: "2.7:32"')
        parser.add_option(
            '-C', "--no-compile", action="store_true",
            help="Don't compile the module, this options implies --running",
            default=False)
        parser.add_option(
            '-r', "--running", action="store_true",
            help='Only use the running Python version',
            default=False)
        parser.add_option(
            '--ignore', action="store_true",
            help='Ignore local changes',
            default=False)
        self.options, args = parser.parse_args()
        if len(args) == 1:
            command = args[0]
        else:
            command = None

        if self.options.no_compile:
            self.options.running = True

        if command == 'clean':
            self.options.verbose = True
        elif command == 'build':
            self.options.running = True
        elif command == 'test_wheel':
            self.wheel = True
        elif command == 'test':
            self.test = True
        elif command == 'testdoc':
            self.test_doc = True
        elif command == 'release':
            if not self.options.tag:
                print("The release command requires the --tag option")
                sys.exit(1)

            self.release = True
            self.wheel = True
            self.test = True
            self.upload = True
        elif command == 'info':
            pass
        else:
            if command:
                print("Invalid command: %s" % command)
            else:
                parser.print_help()
                print("")

            print("Available commands:")
            print("- build: build asyncio in place, imply --running")
            print("- test: run all tests")
            print("- testdoc: test the documentation")
            print("- test_wheel: test building wheel packages")
            print("- release: run tests and publish wheel packages,")
            print("  require the --tag option")
            print("- clean: cleanup the project")
            sys.exit(1)

        if self.options.python and self.options.running:
            print("--python and --running options are exclusive")
            sys.exit(1)

        python = self.options.python
        if python:
            match = re.match("^([23](?:\.([0-9]))?)/(32|64)$", python)
            if not match:
                print("Invalid Python version: %s" % python)
                print('Format of a Python version: "x.y/bits"')
                print("Example: 2.7/32")
                sys.exit(1)
            version = int(match.group(1))
            bits = int(match.group(3))
            version = parse_python_version(version)
            self.python_versions = [PythonVersion(version, bits)]

        if self.options.running:
            self.python_versions = [PythonVersion.running()]

        self.verbose = self.options.verbose
        self.command = command

    def info(self):
        print("Project: %s" % self.project)
        print("Python versions:")
        for pyver in self.python_versions:
            executable = pyver.get_executable(self)
            print("- %s: %s" % (pyver, executable))
        if self.debug_env_var:
            is_set = bool(os.environ.get(self.debug_env_var, ''))
            is_set = "set" if is_set else "not set"
            print("Debug environment variable: %s (%s)"
                  % (self.debug_env_var, is_set))

    def main(self):
        self.parse_options()

        print("Directory: %s" % self.root)
        os.chdir(self.root)

        if self.command == "clean":
            self.cleanup()
            sys.exit(1)

        if self.command == "info":
            self.info()
            sys.exit(1)

        if self.command == "build":
            if len(self.python_versions) != 1:
                print("build command requires one specific Python version")
                print("Use the --python command line option")
                sys.exit(1)
            pyver = self.python_versions[0]
            self.build_inplace(pyver)

        if (self.register or self.upload) and (not self.options.ignore):
            lines = self.scm.get_local_changes()
        else:
            lines = ()
        if lines:
            print("ERROR: Found local changes")
            for line in lines:
                print(line)
            print("")
            print("Revert local changes")
            print("or use the --ignore command line option")
            sys.exit(1)

        scm_tag = self.options.tag
        if scm_tag:
            print("Update repository to revision %s" % scm_tag)
            self.scm.checkout(scm_tag)

        scm_rev = self.scm.get_revision()

        if self.wheel:
            for pyver in self.python_versions:
                self.test_wheel(pyver)

        if self.test:
            self.run_all_tests()
        elif self.test_doc:
            self.check_doc()

        if self.register:
            self.run_command(sys.executable, 'setup.py', 'register')

        if self.sdist:
            self.sdist_upload()

        if self.upload:
            for pyver in self.python_versions:
                self.publish_wheel(pyver)

        print("")
        print("%s revision: %s" % (self.scm.NAME, scm_rev))
        if self.command == 'build':
            print("Inplace compilation done")
        if self.wheel:
            print("Compilation of wheel packages succeeded")
        if self.test:
            print("Tests succeeded")
        if self.register:
            print("Project registered on the Python cheeseshop (PyPI)")
        if self.sdist:
            print("Project source code uploaded to the Python "
                  "cheeseshop (PyPI)")
        if self.upload:
            print("Wheel packages uploaded to the Python cheeseshop (PyPI)")
        for pyver in self.python_versions:
            print("- %s" % pyver)

        scm_rev2 = self.scm.get_revision()
        if scm_rev != scm_rev2:
            print("ERROR: The %s revision changed during the execution" % self.scm.NAME)
            print("Start: %s" % scm_rev)
            print("End: %s" % scm_rev2)
            sys.exit(1)


if __name__ == "__main__":
    Releaser().main()
