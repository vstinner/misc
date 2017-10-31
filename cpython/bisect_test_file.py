"""
One test file only fails when run sequentially.
Find which tests should be run before.
"""
import os.path
import random
import subprocess
import sys

MIN_TESTS = 5
FAILING_TEST = 'test_multiprocessing_fork'

def list_tests():
    args = [sys.executable, '-u', '-m', 'test', '-u', 'all', '--list-tests']
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
    print("+ %s" % ' '.join(args))
    with proc:
        stdout = proc.communicate()[0]
        exitcode = proc.wait()
    if exitcode:
        sys.exit(exitcode)
    return stdout.splitlines()

def runtests(filename):
    args = [sys.executable, '-u', '-m', 'test', '-u', 'all', '--fromfile', filename]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
    print("+ %s" % ' '.join(args))
    with proc:
        result = "<ERROR>"
        prefix = "Tests result: "
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            print(line)
            if prefix in line:
                result = line[len(prefix):]

        exitcode = proc.wait()
    if exitcode:
        sys.exit(exitcode)
    return result

def remove_tests(tests, size):
    selected = set(random.sample(tests[:-1], size))
    # keep the order
    return [test for test in tests if test in selected] + [FAILING_TEST]

def read_tests(filename):
    tests = []
    with open(filename, encoding="utf8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            tests.append(line)
    print("Read %s tests from %s" % (len(tests), filename))
    return tests

def write_tests(filename, tests):
    print("Write %s tests into %s" % (len(tests), filename))
    with open(filename, "w", encoding="utf8") as fp:
        for name in tests:
            fp.write("%s\n" % name)

def rename(old_name, new_name):
    print("Rename %s to %s" % (old_name, new_name))
    os.rename(old_name, new_name)

def main():
    start_file = 'tests'
    counter = 2
    if not os.path.exists(start_file):
        tests = list_tests()
        pos = tests.index(FAILING_TEST)
        if pos < 0:
            raise Exception("cannot find %s" % FAILING_TEST)
        tests = tests[:pos+1]
        write_tests(start_file, tests)

    tests = read_tests(start_file)
    ntest = len(tests)
    print("START: %s tests" % ntest)

    # set to False to double check
    bisect = True

    while len(tests) > MIN_TESTS:
        filename = "tests%s" % counter
        counter += 1

        if bisect:
            subset = remove_tests(tests, max(ntest // 2, 3))
        else:
            subset = tests
        write_tests(filename, subset)
        print("Run %s tests" % len(subset))
        result = runtests(filename)
        print("***")
        print()

        if result in ('SUCCESS', 'ENV CHANGED'):
            rename(filename, filename + "_ok")
            # Drop subset, we want a failure!
            success = True
        elif result == 'FAILURE':
            rename(filename, filename + "_fail")
            if bisect:
                # tests failed: good! continue to bisect
                tests = subset
            success = False
        else:
            print("ERROR: unknown test result: %r" % result)
            sys.exit(1)

        if not bisect:
            if success:
                print("ERROR: tests succeeded with %s" % FAILING_TEST)
            bisect = True


if __name__ == "__main__":
    main()
