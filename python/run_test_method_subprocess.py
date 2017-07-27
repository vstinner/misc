import subprocess
import sys
import time


def read_cases():
    cases = []
    with open("cases") as fp:
        for line in fp:
            cases.append(line.rstrip())
    return cases


def run_test(match):
    cmd = [sys.executable, '-m', 'test', '--fail-env-changed', '--match', match, 'test_multiprocessing_spawn']
    print('+ ' + ' '.join(cmd))
    proc = subprocess.run(cmd)
    return proc.returncode


def main():
    main_start_time = time.monotonic()
    cases = read_cases()
    result = []

    interrupted = False
    try:
        for index, case in enumerate(cases, 1):
            print("Test case %s/%s" % (index, len(cases)))

            start_time = time.monotonic()
            exitcode = run_test(case)
            dt = time.monotonic() - start_time
            if exitcode:
                result.append((case, exitcode, dt))
    except KeyboardInterrupt:
        interrupted = True

    if result:
        for case, exitcode, dt in result:
            print("[%.1f sec] %s: exit code %s" % (dt, case, exitcode))
    else:
        print("All test cases succeeded!")

    dt = time.monotonic() - main_start_time
    print("Total tests duration: %.1f sec" % dt)
    if interrupted:
        print("Interrupted! (CTRL+c)")


if __name__ == "__main__":
    main()
