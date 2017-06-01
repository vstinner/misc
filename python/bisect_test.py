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


def run_tests(tests):
    with tempfile.NamedTemporaryFile() as tmp:
        write_tests(tmp.name, tests)

        cmd = [sys.executable, '-m', 'test', '--matchfile', tmp.name, '-R', '3:3', 'test_threading']
        proc = subprocess.run(cmd)
        return proc.returncode

def main():
    in_filename = "bisect"
    dest_filename = "bisect2"
    max_tests = 1

    with open(in_filename) as fp:
        tests = [line.strip() for line in fp]

    while len(tests) > max_tests:
        ntest = len(tests)
        ntest = max(ntest // 2, 1)
        subtests = random.sample(tests, ntest)
        exitcode = run_tests(subtests)
        print("ran %s tests/%s" % (ntest, len(tests)))
        print("exit", exitcode)
        if exitcode:
            print("Tests failed: use this new subtest")
            tests = subtests
            write_tests(dest_filename, tests)
            print("Tests written into %s" % dest_filename)
        else:
            print("Tests succeeded: skip this subtest, try a new subbset")

if __name__ == "__main__":
    main()
