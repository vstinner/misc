#!/usr/bin/env python3
import argparse
import os.path
import random
import re
import subprocess
import sys
import tempfile


def write_tests(filename, tests):
    with open(filename, "w") as fp:
        for name in tests:
            print(name, file=fp)
        fp.flush()


def run_tests(test_name, tests):
    tmp = tempfile.mktemp()
    try:
        write_tests(tmp, tests)

        cmd = [sys.executable, '-m', 'test',
               '--matchfile', tmp,
               '-R', '3:3',
               test_name]
        proc = subprocess.run(cmd)
        return proc.returncode
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('test_name',
                        help='Test name like test_threading')
    parser.add_argument('input',
                        help='Test names produced by --list-tests written '
                             'into a file')
    parser.add_argument('output',
                        help='Result of the bisection')
    parser.add_argument('-n', '--max-tests', type=int, default=1,
                        help='Maximum number of tests to stop the bisection '
                             '(default: 1)')
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input) as fp:
        tests = [line.strip() for line in fp]

    while len(tests) > args.max_tests:
        ntest = len(tests)
        ntest = max(ntest // 2, 1)
        subtests = random.sample(tests, ntest)
        try:
            exitcode = run_tests(args.test_name, subtests)
        except KeyboardInterrupt:
            print()
            print("Interrupted, exit")
            return

        print("ran %s tests/%s" % (ntest, len(tests)))
        print("exit", exitcode)
        if exitcode:
            print("Tests failed: use this new subtest")
            tests = subtests
            write_tests(args.output, tests)
            print("Tests written into %s" % args.output)
        else:
            print("Tests succeeded: skip this subtest, try a new subbset")


if __name__ == "__main__":
    main()
