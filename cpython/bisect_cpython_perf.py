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


def normpath(path):
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return path


def parse_config(filename):
    conf = types.SimpleNamespace()
    cfgobj = configparser.ConfigParser()
    if not cfgobj.read(filename):
        print("ERROR: failed to read configuration file %s" % filename)
        sys.exit(1)

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

    def getpath(section, key, default=None):
        path = getstr(section, key, default)
        return normpath(path)

    # mandatory config
    conf.old_commit = getstr('config', 'old_commit')
    conf.new_commit = getstr('config', 'new_commit')
    conf.benchmark = getargs('config', 'benchmark')
    conf.benchmark = (normpath(conf.benchmark[0]),) + conf.benchmark[1:]

    # optional config
    conf.work_dir = getpath('config', 'work_dir', os.path.curdir)
    conf.src_dir = getpath('config', 'src_dir', os.path.curdir)
    conf.make_command = getargs('config', 'make_command', 'make')
    conf.benchmark_opts = getargs('config', 'benchmark_opts',
                                  '--inherit-environ=PYTHONPATH -p5 -v')
    conf.configure_args = getargs('config', 'configure_args',
                                  '--with-lto')
    conf.python_path = getstr('config', 'PYTHONPATH', '')
    if conf.python_path:
        conf.python_path = ':'.join(normpath(path) for path in conf.python_path.split(':'))
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
        self._old_bench = None
        self._new_bench = None

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

    def prepare_ref(self, what, commit, filename):
        self.unlink(filename)

        self.run('git', 'checkout', commit, cwd=self.src_dir)
        self.compile_bench(filename)

        bench = perf.Benchmark.load(filename)
        mean = bench.mean()
        print("%s: mean=%s, filename=%s"
              % (what, bench.format_value(mean), filename))

    def get_old_bench(self):
        if self._old_bench is None and os.path.exists(self.old_filename):
            self._old_bench = perf.Benchmark.load(self.old_filename)
        return self._old_bench

    def get_new_bench(self):
        if self._new_bench is None and os.path.exists(self.new_filename):
            self._new_bench = perf.Benchmark.load(self.new_filename)
        return self._new_bench

    def cmd_status(self):
        print("Bisect status")
        print("=============")
        print()
        print("Source directory: %s" % self.src_dir)
        print("Work directory: %s" % self.work_dir)

        old_bench = self.get_old_bench()
        new_bench = self.get_new_bench()
        if old_bench is not None:
            value = old_bench.format_value(old_bench.mean())
            print("Old: mean=%s, commit=%s" % (value, self.conf.old_commit))
        else:
            print("Old: <not computed yet>, commit=%s" % self.conf.old_commit)

        if new_bench is not None:
            value = new_bench.format_value(new_bench.mean())
            if old_bench is not None:
                before = old_bench.mean()
                after = new_bench.mean()
                percent = ((after - before) * 100 / before)
                value += " (%+.0f%%)" % percent
            print("New: mean=%s, commit=%s" % (value, self.conf.new_commit))
        else:
            new_bench = None
            print("New: <not computed yet>, commit=%s" % self.conf.new_commit)

        if old_bench is not None and new_bench is not None:
            if old_bench.mean() > new_bench.mean():
                print("Old > New: speed up, find the first commit "
                      "which introduced the optimization")
            else:
                print("Old < New: slowdown, find the first commit "
                      "which introduced the performance regression")

        path = os.path.join(self.json_dir, '*.json')
        files = glob.glob(path)
        print("JSON files: %s" % len(files))

    def cmd_start(self):
        old_commit = self.conf.old_commit
        new_commit = self.conf.new_commit

        # FIXME: make sure that date(old_commit) < date(new_commit)?

        self.unlink(self.config_cache)
        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)

        if not os.path.exists(self.old_filename):
            self.prepare_ref("Old commit (good)", old_commit,
                             self.old_filename)
        if not os.path.exists(self.new_filename):
            self.prepare_ref("New commit (bad)", new_commit,
                             self.new_filename)

        self.run('git', 'bisect', 'reset', cwd=self.src_dir)
        self.run('git', 'bisect', 'start', cwd=self.src_dir)
        self.run('git', 'bisect', 'good', old_commit, cwd=self.src_dir)
        self.run('git', 'bisect', 'bad', new_commit, cwd=self.src_dir)

        print()
        self.cmd_status()

        print()
        print("Now use the 'run' command to run the bisection")

    def cmd_run(self):
        if self.get_old_bench() is None or self.get_new_bench() is None:
            print("ERROR: First run the start command")
            sys.exit(1)

        self.git_reset()

        while True:
            commit = self.get_git_commit()
            print("Bisect: commit %s" % commit)

            try:
                bad = self.bench_compare(commit=commit)
                result = 'bad' if bad else 'good'
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

    def check_mean(self, bench, old_bench, new_bench):
        mean = bench.mean()
        old_mean = old_bench.mean()
        new_mean = new_bench.mean()

        fmt = bench.format_value
        if old_mean <= new_mean:
            # slowdown: find the first commit which made Python slower.
            # BAD means slower.
            limit = old_mean + (new_mean - old_mean) * 0.75
            bad = (mean >= limit)
            if bad:
                msg = 'BAD (slower)! %s >= %s'
            else:
                msg = 'good (fast): %s < %s'
        else:
            # old_mean > new_mean, speed up: find the first commit which made
            # Python faster. BAD means faster.
            limit = new_mean + (old_mean - new_mean) * 0.25
            bad = (mean <= limit)
            if bad:
                msg = 'BAD (faster)! %s <= %s'
            else:
                msg = 'good (slow): %s > %s'

        mean = "%s (bench mean)" % fmt(mean)
        limit = "%s (bisect limit)" % fmt(limit)

        msg = msg % (mean, limit)
        msg += "; old_mean=%s, new_mean=%s" % (fmt(old_mean), fmt(new_mean))
        print("BISECT RESULT: %s" % msg)

        return bad

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

    def _compile_bench(self, filename, commit=None):
        build_dir = self.build_dir

        self.unlink(filename)

        self.recreate_directory(build_dir)
        if commit is None:
            commit = self.get_git_commit()

        # ./configure
        configure = os.path.join(self.src_dir, 'configure')
        cmd = (configure, '--cache-file=%s' % self.config_cache)
        cmd += self.conf.configure_args
        if self.run_nocheck(*cmd, cwd=build_dir):
            raise BisectError("configure failed")

        # make
        cmd = self.conf.make_command
        if self.run_nocheck(*cmd, cwd=build_dir):
            raise BisectSkip("make failed")

        python = os.path.join(build_dir, 'python')
        if sys.platform in ('darwin', 'win32'):
            python += '.exe'

        # python [benchmark] -o bench.json [options]
        cmd = (python,)
        cmd += self.conf.benchmark
        cmd += ('-o', filename)
        cmd += self.conf.benchmark_opts
        if self.conf.python_path:
            env = dict(os.environ, PYTHONPATH=self.conf.python_path)
        else:
            env = None
        if self.run_nocheck(*cmd, cwd=build_dir, env=env):
            raise BisectError("benchmark failed")

        # revert local changes: sometimes, make modifies some files
        self.git_reset()

        # Update metadata
        metadata = {'commit_id': commit}
        bench = perf.Benchmark.load(filename)
        bench.update_metadata(metadata)
        bench.dump(filename, replace=True)

        value = bench.format_value(bench.mean())
        print("Commit %s: mean %s" % (commit, value))
        return bench

    def compile_bench(self, filename=None, commit=None):
        if not filename:
            if not commit:
                commit = self.get_git_commit()
            filename = os.path.join(self.json_dir, 'bench-%s.json' % commit)

        if not os.path.exists(filename):
            bench = self._compile_bench(filename, commit=commit)
        else:
            bench = perf.Benchmark.load(filename)
        print("Commit %s result: mean=%s, filename=%s"
              % (commit, bench.format_value(bench.mean()), filename))
        return bench

    def cmd_bench(self):
        revision = self.args.revision
        if revision:
            self.run('git', 'checkout', revision, cwd=self.src_dir)

        filename = self.args.output
        if filename:
            filename = os.path.abspath(filename)

        self.compile_bench(filename)

    def bench_compare(self, commit=None):
        old_bench = self.get_old_bench()
        if old_bench is None:
            print("ERROR: missing old bench: run start command")
            sys.exit(1)

        new_bench = self.get_new_bench()
        if new_bench is None:
            print("ERROR: missing new bench: run start command")
            sys.exit(1)

        bench = self.compile_bench(commit=commit)

        return self.check_mean(bench, old_bench, new_bench)

    def cmd_bench_compare(self):
        bad = self.bench_compare()
        exitcode = 1 if bad else 0
        sys.exit(exitcode)

    def create_argparser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('config')

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
        self.args.config = normpath(self.args.config)

        self.conf = parse_config(self.args.config)

        script = ('/home/haypo/prog/bench_python/performance/'
                  'performance/benchmarks/bm_xml_etree.py')
        self.bench_args = (script, 'iterparse',
                           '--inherit-environ=PYTHONPATH',
                           '-p5', '-v')

        self.work_dir = os.path.abspath(self.conf.work_dir)
        self.src_dir = os.path.abspath(self.conf.src_dir)
        self.script = os.path.abspath(__file__)

        self.json_dir = os.path.join(self.work_dir, 'bisect_json')
        self.build_dir = os.path.join(self.work_dir, 'bisect_build')
        self.config_cache = os.path.join(self.work_dir, 'bisect_config.cache')

        self.old_filename = os.path.join(self.json_dir, 'old_commit.json')
        self.new_filename = os.path.join(self.json_dir, 'new_commit.json')
        return parser

    def cmd_reset(self):
        self.rmtree(self.json_dir)
        self.rmtree(self.build_dir)
        self.unlink(self.config_cache)

        # FIXME: remove self.work_dir if it's empty and not the current directory

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
        elif action == 'bench':
            self.cmd_bench()
        elif action == 'bench_compare':
            self.cmd_bench_compare()
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    Bisect().main()
