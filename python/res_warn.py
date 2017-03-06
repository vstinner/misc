"""
Tool to get the origin of ResourceWarning warnings on files and sockets.

Run python with -Wd to display warnings and call enable().

Use the new tracemalloc added in Python 3.4 beta 1.

Limitation: it does not work for text files, only for binary files. See:
http://bugs.python.org/issue19829

--

FileIO constructor calls ResourceWarning with the text representation of the
file, so ResourceWarning constructor does not have access to the file object.

Replacing ResourceWarning class in __builtins__ does not work because io.FileIO
destructor has an hardcoded reference to ResourceWarning.

Replacing io.FileIO doesn't work neither because io.open has an hardcoded
reference to io.FileIO.

Replacing warnings.showwarning to inspect the frame of the caller does not
work because the FileIO destructor is called when the last reference to the
file is set to None. So there is no more reference to the file.
"""
from io import FileIO as _FileIO
from socket import socket as _socket
import _pyio
import builtins
import linecache
import socket
import sys
import traceback
import tracemalloc
import warnings

def warn_unclosed(obj, delta=1):
    delta += 1
    tb = tracemalloc.get_object_traceback(obj)
    if tb is None:
        return
    try:
        warnings.warn("unclosed %r" % obj, ResourceWarning, delta + 1)
        print("Allocation traceback (most recent first):")
        for frame in tb:
            print("  File %r, line %s" % (frame.filename, frame.lineno))
            line = linecache.getline(frame.filename, frame.lineno)
            line = line.strip()
            if line:
                print("    %s" % line)

        if 0:
            frame = sys._getframe(delta)
            tb = traceback.format_stack(frame)
            print("Destroy traceback (most recent last):")
            for line in tb:
                sys.stdout.write(line)
            sys.stdout.flush()
    finally:
        obj.close()

class MyFileIO(_FileIO):
    if 0:
        def __init__(self, *args, **kw):
            _FileIO.__init__(self, *args, **kw)
            tb = tracemalloc.get_object_traceback(self)
            if tb is None:
                raise RuntimeError("tracemalloc is disabled")

    def __del__(self):
        if not self.closed:
            warn_unclosed(self)
        if hasattr(_FileIO, '__del__'):
            _FileIO.__del__(self)

class MySocket(_socket):
    if 0:
        def __init__(self, *args, **kw):
            _socket.__init__(self, *args, **kw)
            tb = tracemalloc.get_object_traceback(self)
            if tb is None:
                raise RuntimeError("tracemalloc is disabled")

    def __del__(self):
        if not self._closed:
            warn_unclosed(self)
        if hasattr(_socket, '__del__'):
            _socket.__del__(self)

def patch_open():
    # Already patched
    if _pyio.FileIO is MyFileIO:
        return

    # _io.open() uses an hardcoded reference to _io.FileIO
    # use _pyio.open() which lookup for FilIO in _pyio namespace
    _pyio.FileIO = MyFileIO
    builtins.open = _pyio.open

def patch_socket():
    socket.socket = MySocket

def enable(nframe=25):
    if not tracemalloc.is_tracing():
        tracemalloc.start(nframe)
    patch_open()
    patch_socket()

def main():
    tracemalloc.start(25)

    print("=== test unbuferred file ===")
    patch_open()
    f = open(__file__, "rb", 0)
    f = None
    print()

    print("=== test socket ===")
    patch_socket()
    s = socket.socket()
    s = None
    print()

if __name__ == "__main__":
    main()

