#!/usr/bin/env python3
"""
Run testtools.run on each filename passed on the command line.

Helper to find a subset of tests which pass on Python 3 for OpenStack.
"""
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

RAN_TESTS_REGEX = re.compile(b"^Ran ([0-9]+) tests? in [0-9.]+s", re.M)


def check(filename):
    argv = ["python", "-m", "testtools.run", "--failfast", filename]
    proc = subprocess.Popen(argv,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    with proc:
        stdout, _ = proc.communicate()
        exitcode = proc.wait()

    if exitcode != 0:
        return (False, 0, filename)

    match = RAN_TESTS_REGEX.search(stdout)
    if not match:
        print("FATAL ERROR: failed to parse test output:")
        print(stdout)
        sys.exit(1)
    ntest = int(match.group(1))
    return (True, ntest, filename)

def main():
    filenames = sys.argv[1:]
    if not filenames:
        print("usage: %s test1 test2 ..." % sys.argv[0])
        sys.exit(1)
    filenames = sorted(set(filenames))

    parallel = os.cpu_count() + 1

    test_succeeded = []
    test_failed = []
    test_empty = []
    start = time.monotonic()
    if parallel > 1:
        print("Test %s files with %s parallel processes..."
              % (len(filenames), parallel))
        with Pool(parallel) as pool:
            results = pool.map(check, filenames)
        for success, ntest, filename in results:
            if not success:
                test_failed.append(filename)
            elif ntest == 0:
                test_empty.append(filename)
            else:
                test_succeeded.append(filename)
    else:
        for index, filename in enumerate(filenames, 1):
            dt = time.monotonic() - start
            print("Checking %s (%s/%s) [%.1f sec]"
                  % (filename, index, len(filenames), dt))
            success, ntest, filename = check(filename)
            if not success:
                test_failed.append(filename)
            elif ntest == 0:
                test_empty.append(filename)
            else:
                test_succeeded.append(filename)
        print()

    print("Fail (%s):" % len(test_failed))
    for filename in test_failed:
        print(filename)
    print()

    print("Success but with 0 test run (%s):" % len(test_empty))
    for filename in test_empty:
        print(filename)
    print()

    print("Succeded (%s):" % len(test_succeeded))
    for filename in test_succeeded:
        print(filename)
    print()

    print("Success: %s(+%s empty)/%s"
          % (len(test_succeeded), len(test_empty), len(filenames)))
    dt = time.monotonic() - start
    print("Total: %.1f sec" % dt)

if __name__ == "__main__":
    main()
