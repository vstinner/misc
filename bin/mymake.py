#!/usr/bin/env python3
import os
import subprocess
import sys
import time

patterns = (
    ('error', 'error: '),
    ('warning', 'warning: '),
)

def main():
    start_time = time.perf_counter()

    env = dict(os.environ)
    # Disable French locale to be able to search for "warning:" in logs
    env['LANG'] = ''

    cmd = ['make', *sys.argv[1:]]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True)

    matched = []
    with proc:
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    # process completed
                    break
                print(line, end="")
                for name, pattern in patterns:
                    if pattern not in line:
                        continue
                    matched.append(line.rstrip())
        except:
            proc.kill()
            raise

        exitcode = proc.wait()

    if matched:
        print()
        for line in matched:
            print(line)
        print(f"=> Found {len(matched)} compiler warnings/errors")

    duration = time.perf_counter() - start_time
    duration = f"{duration:.1f} sec)"
    print()
    if exitcode:
        print(f"Build FAILED with exit code {exitcode} ({duration})")
    elif matched:
        print(f"Build OK but with some warnings/errors ({duration})")
    else:
        print(f"Build OK: no compiler warnings or errors ({duration})")


if __name__ == "__main__":
    main()
