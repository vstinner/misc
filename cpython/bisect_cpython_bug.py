#!/usr/bin/env python3
"""
Usage:

bisect.py bisect.conf start
bisect.py bisect.conf run
bisect.py bisect.conf reset
"""
import argparse
import configparser
import glob
import os.path
import perf
import shlex
import shutil
import subprocess
import sys
import types


def parse_config():
    conf = types.SimpleNamespace()

    def getstr(section, key, default=None):
        try:
            sectionobj = cfgobj[section]
            value = sectionobj[key]
        except KeyError:
            if default is None:
                raise
            return default

        # strip comments
        value = value.partition('#')[0]
        # strip spaces
        return value.strip()

    def getargs(section, key, default=None):
        return tuple(getstr(section, key, default).split())

    # mandatory config
    conf.old_commit = '34cba334034ddef3b32e47bf94cb7d224cfaf15d'
    conf.new_commit = '9b47af65375fab9318e88ccb061394a36c8c6c33'

    # optional config
    conf.src_dir = os.path.abspath(os.getcwd())
    conf.configure_args = ('--with-pydebug',)
    conf.make_command = ('make',)

    bug_script = os.path.join(conf.src_dir, 'bug2.py')
    conf.test_command = (bug_script,)
    return conf


class BisectSkip(SystemExit):
    def __init__(self, msg):
        super().__init__(125)
        self.msg = msg


class BisectError(BisectSkip):
    pass


class Bisect:
    def __init__(self):
        self.args = None
        self.conf = None

    def _subprocess(self, cmd, kwargs):
        if 'cwd' not in kwargs:
            raise ValueError("missing cwd argument")

        print("+ " + ' '.join(map(shlex.quote, cmd)))
        return subprocess.Popen(cmd, **kwargs)

    def _kill_wait_process(self, proc):
        try:
            proc.terminate()
            proc.kill()
        except OSError:
            # process erminated
            pass

        proc.wait()

    def run_nocheck(self, *cmd, **kwargs):
        proc = self._subprocess(cmd, kwargs)

        try:
            proc.wait()
        except:
            self._kill_wait_process(proc)
            raise

        return proc.returncode

    def run(self, *cmd, **kwargs):
        exitcode = self.run_nocheck(*cmd, **kwargs)
        if exitcode:
            sys.exit(exitcode)

    def get_output_nocheck(self, *cmd, **kwargs):
        kwargs['stdout'] = subprocess.PIPE
        kwargs['universal_newlines'] = True
        proc = self._subprocess(cmd, kwargs)
        try:
            stdout = proc.communicate()[0]
        except:
            self._kill_wait_process(proc)
            raise

        exitcode = proc.returncode
        stdout = stdout.rstrip()
        return (exitcode, stdout)

    def get_output(self, *cmd, **kwargs):
        exitcode, stdout = self.get_output_nocheck(*cmd, **kwargs)
        if exitcode:
            sys.exit(exitcode)
        return stdout

    def git_reset(self, error_exitcode=1):
        cmd = ('git', 'reset', '--hard', 'HEAD')
        if self.run_nocheck(*cmd, cwd=self.src_dir):
            sys.exit(error_exitcode)

    def unlink(self, filename):
        if not os.path.exists(filename):
            return

        print("Remove %s" % filename)
        os.unlink(filename)

    def cmd_status(self):
        print("Bisect status")
        print("=============")
        print()
        print("Source directory: %s" % self.src_dir)
        print("Build directory: %s" % self.build_dir)
        print("Config cache: %s" % self.config_cache)
        print("Old commit (good): %s" % self.conf.old_commit)
        print("New commit (bad): %s" % self.conf.new_commit)

    def cmd_start(self):
        old_commit = self.conf.old_commit
        new_commit = self.conf.new_commit

        # FIXME: make sure that date(old_commit) < date(new_commit)?

        self.unlink(self.config_cache)

        print("Old commit (good): %s" % old_commit)
        print("New commit (bad): %s" % new_commit)

        self.run('git', 'bisect', 'reset', cwd=self.src_dir)
        self.run('git', 'bisect', 'start', cwd=self.src_dir)
        self.run('git', 'bisect', 'good', old_commit, cwd=self.src_dir)
        self.run('git', 'bisect', 'bad', new_commit, cwd=self.src_dir)

        print()
        self.cmd_status()

        print()
        print("Now use the 'run' command to run the bisection")

    def cmd_run(self):
        self.git_reset()

        reconfigure = True
        while True:
            commit = self.get_git_commit()
            print("Bisect: commit %s" % commit)

            try:
                ok = self.cmd_test(reconfigure=reconfigure)
                reconfigure = False
                result = 'good' if ok else 'bad'
            except BisectSkip as exc:
                print("ERROR: %s. Skip commit" % exc.msg)
                exitcode = self.run_nocheck('git', 'bisect', 'skip', cwd=self.src_dir)
            except BisectError as exc:
                print("FATAL ERROR: %s. stop bisect!" % exc.msg)
                break
            else:
                print("Bisect result: %s is %s" % (commit, result))

                stdout = self.get_output('git', 'bisect', result, cwd=self.src_dir)
                sys.stdout.write(stdout + "\n")
                sys.stdout.flush()

                lines = stdout.splitlines()
                if lines[0].endswith(' is the first bad commit'):
                    break

        print()
        self.cmd_status()

    def rmtree(self, directory):
        if not os.path.exists(directory):
            return
        print("Remove directory %s" % directory)
        shutil.rmtree(directory)

    def recreate_directory(self, directory):
        self.rmtree(directory)
        os.makedirs(directory)

    def get_git_commit(self):
        cmd = ('git', 'rev-parse', '--verify', 'HEAD')
        exitcode, stdout = self.get_output_nocheck(*cmd, cwd=self.src_dir)
        if exitcode:
            raise BisectError("failed to get the Git commit")
        commit = stdout
        print("Git commit: %s" % commit)
        return commit

    def cmd_test(self, reconfigure=False):
        build_dir = self.build_dir

        if reconfigure:
            self.recreate_directory(build_dir)
        elif not os.path.exists(build_dir):
            os.makedirs(build_dir)

        if reconfigure:
            # ./configure
            configure = os.path.join(self.src_dir, 'configure')
            cmd = (configure, '--cache-file=%s' % self.config_cache)
            cmd += self.conf.configure_args
            if self.run_nocheck(*cmd, cwd=build_dir):
                raise BisectError("configure failed")
        else:
            src = os.path.join(build_dir, 'Modules/Setup.dist')
            dst = os.path.join(build_dir, 'Modules/Setup')
            print("Copy %s to %s" % (src, dst))
            shutil.copyfile(src, dst)

            cmd = ('make', 'clean')
            if self.run_nocheck(*cmd, cwd=build_dir):
                raise BisectError("make clean failed")

        # make
        cmd = self.conf.make_command
        if self.run_nocheck(*cmd, cwd=build_dir):
            raise BisectSkip("make failed")

        python = os.path.join(build_dir, 'python')
        if sys.platform in ('darwin', 'win32'):
            python += '.exe'

        # python [benchmark] -o bench.json [options]
        cmd = (python,) + self.conf.test_command
        exitcode = self.run_nocheck(*cmd, cwd=build_dir)
        print("Test exit code: %s" % exitcode)

        # revert local changes: sometimes, make modifies some files
        self.git_reset()

        return (exitcode == 0)

    def create_argparser(self):
        parser = argparse.ArgumentParser()

        subparsers = parser.add_subparsers(dest='action')

        cmd = subparsers.add_parser('start')
        cmd = subparsers.add_parser('status')
        cmd = subparsers.add_parser('bench_compare')
        cmd = subparsers.add_parser('bench')
        cmd.add_argument('-o', '--output')
        cmd.add_argument('-r', '--revision')
        cmd = subparsers.add_parser('run')
        cmd = subparsers.add_parser('reset')

        return parser

    def init_options(self):
        parser = self.create_argparser()
        self.args = parser.parse_args()

        self.conf = parse_config()

        self.src_dir = os.path.abspath(self.conf.src_dir)
        self.build_dir = os.path.join(self.src_dir, 'build_dir')
        self.config_cache = os.path.join(self.src_dir, 'bisect_config.cache')
        return parser

    def cmd_reset(self):
        self.unlink(self.config_cache)

        self.run('git', 'bisect', 'reset', cwd=self.src_dir)
        self.git_reset()

    def main(self):
        parser = self.init_options()
        action = self.args.action

        if action == 'reset':
            self.cmd_reset()
        elif action == 'start':
            self.cmd_start()
        elif action == 'status':
            self.cmd_status()
        elif action == 'run':
            self.cmd_run()
        elif action == 'test':
            self.cmd_test()
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    Bisect().main()
