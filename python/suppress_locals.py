"""
Test for Python 3.4 creating lightweight "views" of exceptions to avoid the
expensive traceback.format_exception(). The view of the exception can be
used to format the exception later.

It supports chained exceptions, and Exception.__cause__ as well.

See also:

Extracting tracebacks does too much work [open]
http://bugs.python.org/issue17911

Local variables not freed when Exception raises in function called from cycle [wont fix]
http://bugs.python.org/issue5641

asyncio.Future.set_exception() creates a reference cycle [invalid]
http://bugs.python.org/issue20032

Do we need to call gc.collect() occasionally through the event loop?
http://code.google.com/p/tulip/issues/detail?id=42

Traceback objects not properly garbage-collected [invalid]
http://bugs.python.org/issue226254

Reference cycle in _TracebackLogger and bug in _TracebackLogger.__del__()
http://code.google.com/p/tulip/issues/detail?id=155

Twisted fake Traceback object:
http://twistedmatrix.com/trac/browser/trunk/twisted/python/failure.py#L89

frame.f_locals keeps references to things for too long [open since 2009],
request from Twisted
http://bugs.python.org/issue6116
http://twistedmatrix.com/trac/ticket/3853

assertRaises as a context manager keeps tracebacks and frames alive [open]
http://bugs.python.org/issue9815

Expose called function on frame object
http://bugs.python.org/issue12857

tracebacks eat up memory by holding references to locals and globals when they are not wanted [fixed by traceback.clear_frames()]
http://bugs.python.org/issue1565525

Add a frame method to clear expensive details [fixed by frame.clear()]
http://bugs.python.org/issue17934

Generator cleanup without tp_del [rejected]
http://bugs.python.org/issue17807

Generator memory leak [duplicate]
http://bugs.python.org/issue17468

asyncio: remove _TracebackLogger [fixed]
http://bugs.python.org/issue19967

sys.exc_info() should not be stored on a local variable [fixed]
https://code.djangoproject.com/ticket/10758

Capturing the Currently Raised Exception
http://docs.python.org/3/howto/pyporting.html#capturing-the-currently-raised-exception
    In Python 3, the traceback is attached to the exception instance through
    the __traceback__ attribute. If the instance is saved in a local variable
    that persists outside of the except block, the traceback will create a
    reference cycle with the current frame and its dictionary of local
    variables. This will delay reclaiming dead resources until the next cyclic
    garbage collection pass.

    In Python 2, this problem only occurs if you save the traceback itself
    (e.g.  the third element of the tuple returned by sys.exc_info()) in a
    variable.

    => http://hewgill.com/journal/entries/541-python-2-to-3-upgrade-and-exception-handling

[Python-Dev] new unbounded memory leak in exception handling?
https://mail.python.org/pipermail/python-dev/2009-November/094304.html

PEP 3134: Exception Chaining and Embedded Tracebacks [final]
http://legacy.python.org/dev/peps/pep-3134/

PEP 344: Exception Chaining and Embedded Tracebacks [superseded]
http://legacy.python.org/dev/peps/pep-0344/
"""

import traceback
import gc

# ---

def _iter_chain(exc_view, custom_tb=None, seen=None):
    if seen is None:
        seen = set()
    seen.add(exc_view)
    its = []
    context = exc_view.context
    cause = exc_view.cause
    if cause is not None and cause not in seen:
        its.append(_iter_chain(cause, False, seen))
        its.append([(traceback._cause_message, None)])
    elif (context is not None and
          context not in seen):
        its.append(_iter_chain(context, None, seen))
        its.append([(traceback._context_message, None)])

    its.append([(exc_view.exc, custom_tb or exc_view.tb)])
    # itertools.chain is in an extension module and may be unavailable
    for it in its:
        yield from it

def _format_exception_iter(exc_view, limit, chain):
    if chain:
        values = _iter_chain(exc_view, exc_view.tb)
    else:
        values = [(exc_view.exc, exc_view.tb)]

    for value, tb in values:
        if isinstance(value, str):
            # This is a cause/context message line
            yield value + '\n'
            continue
        if tb:
            yield 'Traceback (most recent call last):\n'
            yield from tb.format(limit=limit)
        yield from traceback._format_exception_only_iter(type(value), value)


# ---

class FrameView:
    def __init__(self, frame):
        self.f_code = frame.f_code
        self.f_globals = {}
        for key in ('__loader__', '__name__'):
            if key in frame.f_globals:
                self.f_globals[key] = frame.f_globals[key]
        if frame.f_back is not None:
            self.f_back = FrameView(frame.f_back)
        else:
            self.f_back = None

class TracebackView:
    def __init__(self, tb):
        self.tb_frame = FrameView(tb.tb_frame)
        self.tb_lineno = tb.tb_lineno
        if tb.tb_next is not None:
            self.tb_next = TracebackView(tb.tb_next)
        else:
            self.tb_next = None

    def format(self, limit=None):
        return traceback._format_list_iter(traceback._extract_tb_iter(self, limit=limit))

class ExceptionView:
    def __init__(self, exc):
        self.exc = exc
        self.tb = TracebackView(exc.__traceback__)
        self.cause = None
        self.context = None

    def format(self, limit=None, chain=True):
        return list(_format_exception_iter(self, limit, chain))

def _exception_view(exc, views):
    if exc is None:
        return None
    if exc in views:
        return views[exc]
    suppress_context = exc.__suppress_context__
    view = ExceptionView(exc)
    exc.__traceback__ = None

    view.cause = _exception_view(exc.__cause__, views)
    if not suppress_context:
        view.context = _exception_view(exc.__context__, views)
    exc.__cause__ = None
    exc.__context__ = None
    return view

def exception_view(exc):
    views = {}
    return _exception_view(exc, views)

# ---

class NeverDeleted:
    def __del__(self):
        print("DELETE OBJECT")

def g():
    raise ValueError()

def f():
    g()

def test():
    print("raise exception...")
    try:
        try:
            try:
                obj = NeverDeleted()
                f()
            except Exception:
                raise TypeError()
        except TypeError:
            raise RuntimeError()
    except Exception as exc:
        print("... create exception view")
        later = exception_view(exc)
        print("exit except block")
    gc.collect()
    return later

def main():
    exc_view = test()
    print("format exception:")
    print(''.join(exc_view.format()))
    print("exit")

main()
