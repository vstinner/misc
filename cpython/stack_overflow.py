"""
Links:

* https://github.com/serhiy-storchaka/python-misc/blob/main/stack_overflow.py
* https://discuss.python.org/t/recursion-limits/33869
* https://vstinner.github.io/contrib-cpython-2017q1.html
* https://bugs.python.org/issue46600
* https://bugs.python.org/issue30866
* https://bugs.python.org/issue29227
* https://bugs.python.org/issue28870
* https://bugs.python.org/issue28858
"""

from __future__ import print_function
import sys
import _testcapi
import subprocess


def test_python_iterator(depth):
    class GetStackPointer:
        def __init__(self):
            self.done = False
        def __iter__(self):
            return self
        def __next__(self):
            if not self.done:
                self.done = True
                return _testcapi.stack_pointer()
            else:
                raise StopIteration
        next = __next__

    class I:
        def __init__(self, it):
            self.it = it
        def __iter__(self):
            return self
        def __next__(self):
            return next(self.it)
        next = __next__

    x = iter(GetStackPointer())
    for i in range(depth): x = I(x)
    start = _testcapi.stack_pointer()
    end = next(x)
    return (start, end)

def test_python_call(depth):
    class X:
        def __call__(self, n):
            if n: return self(n-1)
            return _testcapi.stack_pointer()
    start = _testcapi.stack_pointer()
    end = X()(depth)
    return (start, end)

def test_python_getitem(depth):
    class X:
        def __getitem__(self, n):
            if n: return self[n-1]
            return _testcapi.stack_pointer()
    start = _testcapi.stack_pointer()
    end = X()[depth]
    return (start, end)


def worker(test_name, depth, step):
    test = globals()[test_name]
    sys.setrecursionlimit(2**18)
    try:
        while depth < 10**6:
            try:
                sp_start, sp_end = test(depth + step)
            except RecursionError:
                step //= 2
                if step < 10:
                    return
                continue
            else:
                depth += step
                step *= 2

            stack_size = abs(sp_start - sp_end)
            print(depth, stack_size, flush=True)
    except:
        print('ERROR: %r depth=%d' % (sys.exc_info()[1], depth), file=sys.stderr)
        sys.exit(1)

def run_worker(tests):
    total_depth = 0
    total_stack_size = 0
    for test in tests:
        step = 10
        stack_size = None
        depth = 50
        retry = 0
        stop = "crash"
        while True:
            cmd = [sys.executable, __file__, test, str(depth), str(step)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.wait()

            try:
                line = stdout.splitlines()[-1]
                new_depth, new_stack_size = line.split()
                new_depth = int(new_depth)
                new_stack_size = int(new_stack_size) / new_depth
            except IndexError:
                pass
            else:
                depth = max(depth, new_depth)
                if stack_size is not None:
                    stack_size = min(stack_size, new_stack_size)
                else:
                    stack_size = new_stack_size
            if process.returncode == 0:
                stop = "recursion error"
            if b"RecursionError" in stderr:
                stop = "recursion error"
                break
            if step == 1:
                break
            if step > 1:
                step //= 2
            else:
                retry += 1
            if retry > 10:
                break

            depth += step

        if not stack_size:
            stack_size = 0
        print(f"{test}: {depth:,} calls before {stop}, stack: {stack_size:.1f} bytes/call")
        total_depth += depth
        total_stack_size += stack_size

    print()
    print(f"=> total: {total_depth:,} calls and {total_stack_size:.1f} bytes per call")


if __name__ == '__main__':
    if len(sys.argv) > 3:
        test_name = sys.argv[1]
        depth = int(sys.argv[2])
        step = int(sys.argv[3])
        worker(test_name, depth, step)
    else:
        if len(sys.argv) > 1:
            tests = [sys.argv[1]]
        else:
            tests = [test for test in sorted(globals()) if test.startswith('test_')]
            tests = ['test_python_call', 'test_python_iterator', 'test_python_getitem']

        run_worker(tests)

