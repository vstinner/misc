#!/usr/bin/env python3
import argparse
import os.path
import perf
import shlex
import shutil
import signal
import subprocess
import sys


EXIT_SKIP = 125
# 'git bisect run' has no way to signal "errors"?
EXIT_ERROR = EXIT_SKIP


class Bisect:
    def __init__(self):
        self.script = os.path.abspath(__file__)
        self.work_dir = os.path.abspath('.')
        self.build_dir = os.path.join(self.work_dir, 'build')
        self.src_dir = os.path.abspath('.')
        self.config_cache = os.path.join(self.work_dir, 'config.cache')

        self.make_args = ('make',)
        # self.configure_args = ('--with-lto',)
        self.configure_args = ()
        script = ('/home/haypo/prog/bench_python/performance/'
                  'performance/benchmarks/bm_pickle.py')
        self.bench_args = (script, 'unpickle_list',
                           '--inherit-environ=PYTHONPATH',
                           '-p5', '-v')
        self.ppid = None

    def sigint_parent(self):
        if self.ppid is None:
            return

        os.kill(self.ppid, signal.SIGINT)

    def run_nocheck(self, *cmd, **kwargs):
        if 'cwd' not in kwargs:
            raise ValueError("missing cwd argument")

        print("+ " + ' '.join(map(shlex.quote, cmd)))
        proc = subprocess.Popen(cmd, **kwargs)

        try:
            proc.wait()
        except:
            try:
                proc.terminate()
                proc.kill()
            except OSError:
                # process terminated
                pass
            proc.wait()
            self.sigint_parent()
            raise

        return proc.returncode

    def run(self, *cmd, **kwargs):
        exitcode = self.run_nocheck(*cmd, **kwargs)
        if exitcode:
            sys.exit(exitcode)

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
        self.run_benchmark(filename)

        bench = perf.Benchmark.load(filename)
        mean = bench.mean()
        print("%s: mean=%s, filename=%s"
              % (what, bench.format_value(mean), filename))

    def run_bisect(self, args):
        # FIXME: make sure that date(left) < date(right)?

        self.unlink(self.config_cache)

        left = os.path.join(self.work_dir, 'left.json')
        self.prepare_ref("Left (good)", args.left, left)

        right = os.path.join(self.work_dir, 'right.json')
        self.prepare_ref("Right (bad)", args.right, right)

        self.run('git', 'bisect', 'reset', cwd=self.src_dir)
        self.run('git', 'bisect', 'start', cwd=self.src_dir)
        self.run('git', 'bisect', 'good', args.left, cwd=self.src_dir)
        self.run('git', 'bisect', 'bad', args.right, cwd=self.src_dir)

        cmd = (sys.executable, self.script, 'bench', left, right)
        cmd = ('git', 'bisect', 'run') + cmd
        self.run(*cmd, cwd=self.src_dir)

    def check_mean(self, bench, left, right):
        mean = bench.mean()
        left = left.mean()
        right = right.mean()

        fmt = bench.format_value
        if left <= right:
            # slowdown: find the first commit which made Python slower.
            # BAD means slower.
            limit = left + (right - left) * 0.75
            bad = (mean >= limit)
            if bad:
                msg = 'BAD (slower)! %s >= %s'
            else:
                msg = 'good (fast): %s < %s'
        else:
            # left > right, speed up: find the first commit which made Python
            # faster. BAD means faster.
            limit = right + (left - right) * 0.25
            bad = (mean <= limit)
            if bad:
                msg = 'BAD (faster)! %s <= %s'
            else:
                msg = 'good (slow): %s > %s'

        mean = "%s (bench mean)" % fmt(mean)
        limit = "%s (bisect limit)" % fmt(limit)

        msg = msg % (mean, limit)
        msg += "; left=%s, right=%s" % (fmt(left), fmt(right))
        print("BISECT RESULT: %s" % msg)

        exitcode = 1 if bad else 0
        sys.exit(exitcode)

    def fatal_error(self):
        self.sigint_parent()
        sys.exit(EXIT_ERROR)

    def run_benchmark(self, filename):
        build_dir = self.build_dir

        self.unlink(filename)

        if os.path.exists(build_dir):
            print("Remove directory %s" % build_dir)
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)

        # ./configure
        configure = os.path.join(self.src_dir, 'configure')
        cmd = (configure, '--cache-file=%s' % self.config_cache)
        cmd += self.configure_args
        if self.run_nocheck(*cmd, cwd=build_dir):
            self.fatal_error()

        # make
        if self.run_nocheck(*self.make_args, cwd=build_dir):
            sys.exit(EXIT_SKIP)

        program = os.path.join(build_dir, 'python')
        if sys.platform in ('darwin', 'win32'):
            program += '.exe'

        # python bench.py -o bench.json
        cmd = (program,) + self.bench_args + ('-o', filename)
        if self.run_nocheck(*cmd, cwd=build_dir):
            self.fatal_error()

    def bench_compare(self, args):
        self.ppid = os.getppid()

        left = perf.Benchmark.load(args.left)
        right = perf.Benchmark.load(args.right)

        filename = os.path.join(self.work_dir, 'json')
        self.run_benchmark(filename)

        bench = perf.Benchmark.load(filename)

        self.check_mean(bench, left, right)

    def create_argparser(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='action')

        cmd = subparsers.add_parser('bisect')
        cmd.add_argument('left', metavar='COMMIT')
        cmd.add_argument('right', metavar='COMMIT')

        cmd = subparsers.add_parser('bench')
        cmd.add_argument('left', metavar='JSON_FILENAME')
        cmd.add_argument('right', metavar='JSON_FILENAME')

        return parser

    def main(self):
        parser = self.create_argparser()
        args = parser.parse_args()

        if args.action == 'bisect':
            self.run_bisect(args)
        elif args.action == 'bench':
            self.bench_compare(args)
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    Bisect().main()
