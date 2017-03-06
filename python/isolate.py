import asyncio.subprocess
import datetime
import logging
import os
import random
import subprocess
import sys
import time

# The failing test that we are trying to isolate
FAILING = "test_os"
TIMEOUT = 20 * 60   # seconds
# Explicit blacklist of tests known to fail randomly, ignore them
BLACKLIST = {}

baseargs = [sys.executable, "-Wd", "-E", "-bb",
            "-m", "test", "-uall", "-r", "--timeout=%s" % TIMEOUT]


def get_tests():
    args = [sys.executable, "-m", "test", "--list-tests"]
    cmd = subprocess.run(args, stdout=subprocess.PIPE, check=True)
    stdout = cmd.stdout.decode('ascii')
    return stdout.split()


class Application:
    def __init__(self):
        self.failing = FAILING
        self.ntest = 10   # number of tests run before failing
        self.parallel = os.cpu_count() + 1  # number of processes running in parallel

        self.uid = 0
        self.loop = None
        self.pending = None

    async def run(self, tests):
        self.uid += 1
        worker_id = self.uid

        start = time.monotonic()

        filename = "tests-%s.txt" % self.uid
        try:
            with open(filename, "x") as fp:
                for test in tests:
                    print(test, file=fp)
            args = [*baseargs, "--fromfile=%s" % filename]
            kw = dict(stdout=asyncio.subprocess.PIPE,
                      stderr=asyncio.subprocess.PIPE,
                      loop=self.loop)

            proc = await asyncio.create_subprocess_exec(*args, **kw)
            print("[worker #%s] pid %s, run %s tests: %s"
                  % (worker_id, proc.pid, len(tests), ' '.join(tests)), flush=True)

            try:
                stdout, stderr = await proc.communicate()
            except:
                proc.kill()
                await proc.wait()
                raise

            returncode = proc.returncode
        finally:
            os.unlink(filename)

        dt = time.monotonic() - start
        ok = bool(returncode)
        if ok:
            print("FAIL", flush=True)

            sys.stdout.flush()
            sys.stdout.buffer.write(stdout)
            sys.stdout.flush()

            sys.stderr.flush()
            sys.stderr.buffer.write(stderr)
            sys.stderr.flush()

            print()
            print("executed tests (%s):" % len(tests))
            print(' '.join(tests))

        return (ok, tests, dt)

    def job(self):
        tests = []
        while len(tests) < self.ntest and self.pending:
            index = random.randrange(len(self.pending))
            name = self.pending.pop(index)
            tests.append(name)
        assert tests
        tests.append(self.failing)
        return self.run(tests)

    async def manager(self):
        loop_start = time.monotonic()
        total_run = 0
        found = None
        tasks = set()
        while self.pending and not found:
            while self.pending and len(tasks) < self.parallel:
                task = self.job()
                tasks.add(task)

            print("run %s workers in parallel" % len(tasks))

            done, tasks = await asyncio.wait(tasks, loop=self.loop, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                ok, tests, dt = task.result()
                if ok:
                    print("FOUND %r!" % (tests,))
                    found = tests
                    break

                total_run += len(tests)
                total_dt = time.monotonic() - loop_start
                eta = len(self.pending) * total_dt / total_run

                print("%s to run %s+1 tests: todo %s tests (ETA %s)"
                      % (datetime.timedelta(seconds=int(dt)),
                         self.ntest,
                         len(self.pending),
                         datetime.timedelta(seconds=int(eta))))
                print(flush=True)

        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.wait(tasks, loop=self.loop)

        total_dt = time.monotonic() - loop_start
        print("Total duration: %s" % datetime.timedelta(seconds=int(eta)))
        return found

    def main(self):
        #logging.basicConfig(level=logging.DEBUG)

        print("failing test: %s" % self.failing)
        print("#test run before failing test: %s" % self.ntest)
        print("#test process run in parallel: %s" % self.parallel)
        print("test blacklist: %s" % sorted(BLACKLIST))
        print()

        if self.failing in BLACKLIST:
            raise Exception("failing test cannot be in the blacklist!")

        tests = get_tests()
        self.pending = sorted(set(tests) - BLACKLIST - {self.failing})
        print("Found %s tests (excluding blacklisted tests and the failing test)"
              % len(self.pending))

        if os.name == 'nt':
            self.loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(self.loop)
        else:
            self.loop = asyncio.get_event_loop()
        try:
            found = self.loop.run_until_complete(self.manager())
        except KeyboardInterrupt:
            # FIXME: handle this in the event loop!
            print("interrupted!")
        self.loop.close()

        print()
        if not found:
            print("failed to isolate the failure :-(")
            sys.exit(1)

        print("success: %s" % ' '.join(found))


if __name__ == "__main__":
    Application().main()
