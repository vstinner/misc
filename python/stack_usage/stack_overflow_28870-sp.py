"""
http://bugs.python.org/issue28870
"""
from __future__ import print_function
import sys
import _testcapi


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


if __name__ == '__main__':
    if len(sys.argv) > 3:
        test = globals()[sys.argv[1]]
        depth = int(sys.argv[2])
        step = int(sys.argv[3])
        sys.setrecursionlimit(2**18)
        try:
            while depth < 10**6:
                sp_start, sp_end = test(depth)
                stack_size = abs(sp_start - sp_end) // depth
                print(depth, stack_size, flush=True)
                sys.stdout.flush()
                depth += step
        except:
            print('ERROR: %r depth=%d' % (sys.exc_info()[1], depth), file=sys.stderr)
            sys.exit(1)

    import subprocess
    if len(sys.argv) > 1:
        tests = [sys.argv[1]]
        globals()[tests[0]]
    else:
        tests = [test for test in sorted(globals()) if test.startswith('test_')]
        tests = ['test_python_call', 'test_python_getitem', 'test_python_iterator']

    total_depth = 0
    total_stack_size = 0
    for test in tests:
        step = 2**14
        stack_size = None
        depth = 0
        retry = 0
        while True:
            cmd = [sys.executable, __file__, test, str(depth + step), str(step)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate(input)
            process.wait()
            try:
                line = stdout.splitlines()[-1]
                new_depth, new_stack_size = line.split()
                new_depth = int(new_depth)
                new_stack_size = int(new_stack_size)
            except IndexError:
                pass
            else:
                depth = max(depth, new_depth)
                if stack_size is not None:
                    stack_size = min(stack_size, new_stack_size)
                else:
                    stack_size = new_stack_size
            #print(test, depth, step, file=sys.stderr)
            if step > 1:
                step //= 2
            else:
                retry += 1
            if retry > 10:
                break

        if not stack_size:
            stack_size = 0
        print("%s: %s calls before crash, stack: %s bytes/call" % (test, depth, stack_size))
        total_depth += depth
        total_stack_size += stack_size

    print()
    print("=> total: %s calls, %s bytes" % (total_depth, total_stack_size))
