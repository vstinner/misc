++++++++++++++++++++++++++++++++++++++++++++++++++++++++
PEP xxx: Modify the C API to hide implementation details
++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Abstract
========

The PEP introduces a few backward incompatible changes in the C API by
making the assumption that `Most C extensions don't rely directly on
CPython internals`_, and proposes a migration plan to continue to
support old unmodified C extensions

* Hide implementation details from the C API to allow implementing
  optimizations in CPython and make PyPy more efficient.
* Continue to support old unmodified C extensions by continuing to
  provide the fully compatible "regular" CPython runtime.
* Provide a new "optimized" but incompatible CPython runtime, using the
  same CPython code base: faster but can only import C extensions which
  don't use implementation details. Features implemented in CPython
  will be available in the regular and in the new runtimes.
* Only build a C extension once and use it on multiple Python runtimes
  and different versions of the same runtime (stable ABI).
* Better advertise alternative Python runtimes and better communicate on
  the difference between the Python language and the Python
  implementation (especially CPython).

Note: Cython and cffi should be preferred to write new C extensions.
This PEP is about existing C extensions which cannot be rewritten with
Cython.


Rationale
=========

To remain competitive in term of performance with other programming
languages like Go or Rust, Python has to become more efficient.

Make Python two times faster
----------------------------

The C API leaks too many implementation details which prevent optimizing
CPython. See `Optimize CPython`_.

PyPy's support for Python's C API (pycext) is slow because it has to
emulate CPython internals like memory layout and reference counting. The
emulation causes memory overhead, memory copies, conversions, etc. See
`Inside cpyext: Why emulating CPython C API is so Hard
<https://morepypy.blogspot.com/2018/09/inside-cpyext-why-emulating-cpython-c.html>`_
(Sept 2018) by Antonio Cuni.

While this PEP may make CPython a little bit slower in the short term,
the long-term goal is to make "Python" at least two times faster. This
goal is not hypothetical: PyPy is already 4.2x faster than CPython and is
fully compatible. C extensions are the bottleneck of PyPy. This PEP
proposes a migration plan to move towards opaque C API which would make
PyPy faster.

Promote the limited C API and the stable API (PEP 384)
------------------------------------------------------

The limited API is not widely used (PyQt is one of the few known users).
It is also not used by default.

The goal of this PEP is to move the default C API towards the limited C
API. The long term goal is that the default C API becomes the limited C
API.

Separated the Python language and the CPython runtime (promote alternative runtimes)
------------------------------------------------------------------------------------

The Python language should be better separated from its runtime. It's
common to say "Python" when referring to "CPython". Even in this PEP :-)

Because the CPython runtime remains the reference implementation, many
people believe that the Python language itself has design flaws which
prevent it from being efficient. PyPy proved that this is a false
assumption: on average, PyPy runs Python code 4.2 times faster than
CPython.

One solution for separating the language from the implementation is to
promote the usage of alternative runtimes: not only provide the regular
CPython, but also PyPy, optimized CPython which is only compatible with
C extensions using the limited C API, CPython compiled in debug mode to
ease debugging issues in C extensions, RustPython, etc.

To make alternative runtimes viable, they should be competitive in term
of features and performance. Currently, C extension modules remain the
bottleneck for PyPy.

Most C extensions don't rely directly on CPython internals
----------------------------------------------------------

While the C API is still tidely coupled to CPython internals, in
practical, most C extensions don't rely directly on CPython internals.

The expectation is that these C extensions will remain compatible with
an "opaque" C API and only a minority of C extensions will have to be
modified.

Moreover, more and more C extensions are implemented in Cython or cffi.
Updating Cython and cffi to be compatible with the opaque C API will
make all these C extensions without having to modify the source code of
each extension.


Flaws of the C API
==================

Borrowed references
-------------------

A borrowed reference is a pointer which doesn't “hold” a reference. If
the object is destroyed, the borrowed reference becomes a dangling
pointer, pointing to freed memory which might be reused by a new object.
Borrowed references can lead to bugs and crashes when misused. An
example of a CPython bug caused by this is `bpo-25750: crash in
type_getattro() <https://bugs.python.org/issue25750>`_.

Borrowed references are a problem whenever there is no reference to
borrow: they assume that a referenced object already exists (and thus
has a positive reference count).

Tagged pointers are an example of this problem: since there is no
concrete ``PyObject*`` to represent the integer, it cannot easily be
manipulated.

This issue complicates optimizations like PyPy's list strategies: if a
list contains only small integers, it is stored as a compact C array of
longs. The equivalent of ``PyObject`` is only created when an item is
accessed. (Most of the time the object is optimized away by the JIT, but
this is another story.) This makes it hard to support the C API function
``PyList_GetItem()``, which should return a reference borrowed from the
list, but the list contains no concrete ``PyObject`` that it could lend a
reference to!  PyPy's current solution is very bad: the first time
``PyList_GetItem()`` is called, the whole list is de-optimized
(converted to a list of ``PyObject*``). See ``cpyext``
``get_list_storage()``.

See also the Specialized list use case, which is the same optimization
applied to CPython. Like in PyPy, this optimization is incompatible with
borrowed references since the runtime cannot guess when the temporary
object should be destroyed.

If ``PyList_GetItem()`` returned a strong reference, the ``PyObject*``
could just be allocated on the fly and destroyed when the user
decrements its reference count. Basically, by putting borrowed
references in the API, we are making it impossible to change the
underlying data structure.

Functions stealing strong references
------------------------------------

There are functions which steal strong references, for example
``PyModule_AddObject()`` and ``PySet_Discard()``. Stealing references is
an issue similar to borrowed references.

PyObject**
----------

Some functions of the C API return a pointer to an array of
``PyObject*``:

* ``PySequence_Fast_ITEMS()``
* ``PyTuple_GET_ITEM()`` is sometimes abused to get an array of all of
  the tuple's contents: ``PyObject **items = &PyTuple_GET_ITEM(0);``

In effect, these functions return an array of borrowed references: like
with ``PyList_GetItem()``, all callers of ``PySequence_Fast_ITEMS()``
assume the sequence holds references to its elements.

Leaking structure members
-------------------------

``PyObject``, ``PyTypeObject``, ``PyThreadState``, etc. structures are
currently public: C extensions can directly read and modify the
structure members.

For example, the ``Py_INCREF()`` macro directly increases
``PyObject.ob_refcnt``, without any abstraction. Hopefully,
``Py_INCREF()`` implementation can be modified without affecting the
API.


Change the C API
================

Separate header files of limited and internal C API
---------------------------------------------------

In Python 3.6, all headers (.h files) were directly in the ``Include/``
directory.

In Python 3.7, work started to move the internal C API into a new
subdirectory, ``Include/internal/``. The work continued in Python 3.8
and 3.9. The internal C API is only partially exported: some functions
are only declared with ``extern`` and so cannot be used outside CPython
(with compilers supporting ``-fvisibility=hidden``, see above), whereas
some functions are exported with ``PyAPI_FUNC()`` to make them usable in
C extensions.  Debuggers and profilers are typical users of the internal
C API to inspect Python internals without calling functions (to inspect
a coredump for example).

Python 3.9 is now built with ``-fvisibility=hidden`` (supported by GCC
and clang): symbols which are not declared with ``PyAPI_FUNC()`` or
``PyAPI_DATA()`` are no longer exported by the dynamical library
(libpython).

Another change is to separate the limited C API from the "CPython" C
API: Python 3.8 has a new ``Include/cpython/`` sub-directory. It should
not be used directly, but it is used automatically from the public
headers when the ``Py_LIMITED_API`` macro is not defined.

**Backward compatibility:** fully backward compatible.

**Status:** basically completed in Python 3.9.

Changes without API changes and with minor performance overhead
---------------------------------------------------------------

* Replace macros with static inline functions. Work started in 3.8 and
  made good progress in Python 3.9.
* Modify macros to avoid directly accessing structures fields.

For example, the `Hide implementation detail of trashcan macros
<https://github.com/python/cpython/commit/38965ec5411da60d312b59be281f3510d58e0cf1>`_
commit modifies ``Py_TRASHCAN_BEGIN_CONDITION()`` macro to call a new
``_PyTrash_begin()`` function rather than accessing directly
``PyThreadState.trash_delete_nesting`` field.

**Backward compatibility:** fully backward compatible.

**Status:** good progress in Python 3.9.

Changes without API changes but with performance overhead
---------------------------------------------------------

Replace macros or inline functions with regular functions. Work started
in 3.9 on a limited set of functions.

Converting macros to function calls can have a small overhead on
performances.

**Backward compatibility:** fully backward compatible.

**Status:** not started. The overhead must be measured with benchmarks
and this PEP should be accepted.

API and ABI incompatible changes
--------------------------------

* Make structures opaque: move them to the internal C API.
* Remove functions from the public C API which are tied to CPython
  internals. Maybe begin by marking these functions as private (rename
  ``PyXXX`` to ``_PyXXX``) or move them to the internal C API.
* Ban statically allocated types (by making ``PyTypeObject`` opaque):
  enforce usage of ``PyType_FromSpec()``.

Examples of issues to make structures opaque:

* ``PyGC_Head``: https://bugs.python.org/issue40241
* ``PyObject``: https://bugs.python.org/issue39573
* ``PyTypeObject``: https://bugs.python.org/issue40170
* ``PyThreadState``: https://bugs.python.org/issue39573

**Backward compatibility:** backward incompatible on purpose. Break the
limited C API and the stable ABI.


CPython specific behavior
=========================

Some C functions and some Python functions have a behavior which is
closely tied to the current CPython implementation.

is operator
-----------

The "x is y" operator is closed tied to how CPython allocates objects
and to ``PyObject*``.

For example, CPython uses singletons for numbers in [-5; 256] range::

    >>> x=1; (x + 1) is 2
    True
    >>> x=1000; (x + 1) is 1001
    False

Python 3.8 compiler now emits a ``SyntaxWarning`` when the right operand
of the ``is`` and ``is not`` operators is a literal (ex: integer or
string), but don't warn if it is ``None``, ``True``, ``False`` or
``Ellipsis`` singleton (`bpo-34850
<https://bugs.python.org/issue34850>`_). Example::

    >>> x=1
    >>> x is 1
    <stdin>:1: SyntaxWarning: "is" with a literal. Did you mean "=="?
    True

CPython PyObject_RichCompareBool
--------------------------------

CPython considers that two objects are identical if their memory address
are equal: ``x is y`` in Python (``IS_OP`` opcode) is implemented
internally in C as ``left == right`` where ``left`` and ``right`` are
``PyObject *`` pointers.

The main function to implement comparison in CPython is
``PyObject_RichCompareBool()``. This function considers that two objects
are equal if the two ``PyObject*`` pointers are equal (if the two
objects are "identical"). For example,
``PyObject_RichCompareBool(obj1, obj2, Py_EQ)`` doesn't call
``obj1.__eq__(obj2)`` if ``obj1 == obj2`` where ``obj1`` and ``obj2``
are ``PyObject*`` pointers.

This behavior is an optimization to make Python more efficient.

For example, the ``dict`` lookup avoids ``__eq__()`` if two pointers are
equal.

Another example are Not-a-Number (NaN) floating pointer numbers which
are not equal to themselves::

    >>> nan = float("nan")
    >>> nan is nan
    True
    >>> nan == nan
    False

The ``list.__contains__(obj)`` and ``list.index(obj)`` methods are
implemented with ``PyObject_RichCompareBool()`` and so rely on objects
identity::

    >>> lst = [9, 7, nan]
    >>> nan in lst
    True
    >>> lst.index(nan)
    2
    >>> lst[2] == nan
    False

In CPython, ``x == y`` is implemented with ``PyObject_RichCompare()``
which don't make the assumption that identical objects are equal.
That's why ``nan == nan`` or ``lst[2] == nan`` return ``False``.


Issues for other Python implementations
---------------------------------------

The Python language doesn't require to be implemented with ``PyObject``
structure and use ``PyObject*`` pointers. PyPy doesn't use ``PyObject``
nor ``PyObject*``. If CPython is modified to use `Tagged Pointers`_,
CPython would have the same issue.

Alternative Python implementations have to mimick CPython to reduce
incompatibilities.

For example, PyPy mimicks CPython behavior for the ``is`` operator with
CPython small integer singletons::

    >>>> x=1; (x + 1) is 2
    True

It also mimicks CPython ``PyObject_RichCompareBool()``. Example with the
Not-a-Number (NaN) float::

    >>>> nan=float("nan")
    >>>> nan == nan
    False
    >>>> lst = [9, 7, nan]
    >>>> nan in lst
    True
    >>>> lst.index(nan)
    2
    >>>> lst[2] == nan
    False



Better advertise alternative Python runtimes
============================================

Currently, PyPy and other "alternative" Python runtimes are not well
advertised on the `Python website <https://www.python.org/>`_. They are
only listed as the last choice in the Download menu.

Once enough C extensions will be compatible with the limited C API, PyPy
and other Python runtimes should be better advertised on the Python
website and in the Python documentation, to no longer introduce them as
as first-class citizen.

Obviously, CPython is likely to remain the most feature-complete
implementation in mid-term, since new PEPs are first implemented in
CPython. Limitations can be simply documented, and users should be free
to make their own choice, depending on their use cases.


HPy project
===========


The `HPy project <https://github.com/pyhandle/hpy>`__ is a brand new C
API written from scratch. It is designed to ease migration from the
current C API and to be efficient on PyPy. HPy hides all implementation
details: it is based on "handles" so objects cannot be inspected with
direct memory access: only opaque function calls are allowed. This
abstraction has many benefits:

* No more ``PyObject`` emulation needed: smaller memory footprint in
  PyPy cpyext, no more expensive conversions.
* It is possible to have multiple handles pointing to the same object.
  It helps to better track the object lifetime and makes the PyPy
  implementation easier. PyPy doesn't use reference counting but a
  tracing garbage collector. When the PyPy GC moves objects in memory,
  handles don't change! HPy uses an array mapping handle to objects:
  only this array has to be updated. It is way more efficient.
* The Python runtime is free to modify deep internals compared to
  CPython. Many optimizations become possible: see `Optimize CPython`_
  section.
* It is easy to add a debug wrapper to add checks before and after the
  function calls. For example, ensure that that GIL is held when calling
  CPython.

HPy is developed outside CPython, is implemented on top of the existing
Python C API, and so can support old Python versions.

By default, binaries compiled in "universal" HPy ABI mode can be used on
CPython and PyPy. HPy can also target CPython ABI which has the same
performance than native C extensions. See HPy documentation of `Target
ABIs documentation
<https://github.com/pyhandle/hpy/blob/feature/improve-docs/docs/overview.rst#target-abis>`_.

The PEP moves the C API towards HPy design and API.


New optimized CPython runtime
==============================

Backward incompatible changes is such a pain for the whole Python
community. To ease the migration (accelerate adoption of the new C
API), one option is to provide not only one but two CPython runtimes:

* Regular CPython: fully backward compatible, support direct access to
  structures like ``PyObject``, etc.
* New optimized CPython: incompatible, cannot import C extensions which
  don't use the limited C API, has new optimizations, limited to the C
  API.

Technically, both runtimes would have the same code base, to ease
maintenance: CPython. The new optimized CPython would be a ./configure
flag to build a different Python. On Windows, it would be a different
project of the Visual Studio solution reusing pythoncore project, but
define a macro to build enable optimization and change the C API.


Cython and cffi
===============

Cython and cffi should be preferred to write new C extensions. This PEP
is about existing C extensions which cannot be rewritten with Cython.

Cython may be modified to add a new build mode where only the "limited C
API" is used.


Use Cases
=========

Optimize CPython
----------------

The new optimized runtime can implement new optimizations since it only
supports C extension modules which don't access Python internals.

Tagged pointers
...............

`Tagged pointer <https://en.wikipedia.org/wiki/Tagged_pointer>`_.

Avoid ``PyObject`` for small objects (ex: small integers, short Latin-1
strings, None and True/False singletons): store the content directly in
the pointer, with a tag for the object type.


Tracing garbage collector
.........................

Experiment with a tracing garbage collector inside CPython. Keep
reference counting for the C API.

One of the issue are functions of the C API which return a pointer like
``PyBytes_AsString()``. Python doesn't know when the caller stops using
the pointer, and so cannot move the object in memory (for a moving
garbage collector). API like ``PyBuffer`` is better since it requires
the caller to call ``PyBuffer_Release()`` when it is done.

Specialized list
................

Specialize lists of small integers: if a list only contains numbers
which fit into a C ``int32_t``, a Python list object could use a more
efficient ``int32_t`` array to reduce the memory footprint (avoid
``PyObject`` overhead for these numbers).

Temporary ``PyObject`` objects would be created on demand for backward
compatibility.

This optimization is less interesting if tagged pointers are
implemented.

PyPy already implements this optimization.

O(1) bytearray to bytes conversion
..................................

Convert bytearray to bytes without memory copy.

Currently, bytearray is used to build a bytes string, but it's usually
converted into a bytes object to respect an API. This conversion
requires to allocate a new memory block and copy data (O(n) complexity).

It is possible to implement O(1) conversion if it would be possible to
pass the ownership of the bytearray object to bytes.

That requires modifying the ``PyBytesObject`` structure to support
multiple storages (support storing content into a separate memory
block).

Fork and "Copy-on-Read" problem
...............................

Solve the "Copy on read" problem with fork: store reference counter
outside ``PyObject``.

Currently, when a Python object is accessed, its ``ob_refcnt`` member is
incremented temporarily to hold a "strong reference" to it (ensure that
it cannot be destroyed while we use it). Many operating system implement
fork() using copy-on-write ("CoW"). A memory page (ex: 4 KB) is only
copied when a process (parent or child) modifies it. After Python is
forked, modifying ``ob_refcnt`` copies the memory page, even if the
object is only accessed in "read only mode".

`Dismissing Python Garbage Collection at Instagram
<https://engineering.instagram.com/dismissing-python-garbage-collection-at-instagram-4dca40b29172>`_
(Jan 2017) by Instagram Engineering.

Instagram contributed `gc.freeze()
<https://docs.python.org/dev/library/gc.html#gc.freeze>`_ to Python 3.7
which works around the issue.

One solution for that would be to store reference counters outside
``PyObject``. For example, in a separated hash table (pointer to
reference counter). Changing ``PyObject`` structures requires that C
extensions don't access them directly.

Debug runtime and remove debug checks in release mode
.....................................................

If the C extensions are no longer tied to CPython internals, it becomes
possible to switch to a Python runtime built in debug mode to enable
runtime debug checks to ease debugging C extensions.

If using such a debug runtime becomes harder, indirectly it means that
runtime debug checks can be removed from the release build. CPython code
base is still full of runtime checks calling ``PyErr_BadInternalCall()``
on failure. Removing such checks in release mode can make Python more
efficient.

PyPy
----

ujson is 3x faster on PyPy when using HPy instead of the Python C API.
See `HPy kick-off sprint report
<https://morepypy.blogspot.com/2019/12/hpy-kick-off-sprint-report.html>`_
(December 2019).


GraalPython
-----------

`GraalPython <https://github.com/graalvm/graalpython>`_ is a Python 3
implementation built on `GraalVM <https://www.graalvm.org/>`_
("Universal VM for a polyglot world"). It is interested in supporting
HPy.  See `Leysin 2020 Sprint Report
<https://morepypy.blogspot.com/2020/03/leysin-2020-sprint-report.html>`_.
It would also benefit of this PEP.


Rust-CPython
------------

Rust-CPython is interested in supporting HPy.
See `Leysin 2020 Sprint Report
<https://morepypy.blogspot.com/2020/03/leysin-2020-sprint-report.html>`_.

RustPython and PyO3 would also benefit of this PEP.

Links:

* `PyO3 <https://github.com/PyO3/pyo3>`_:
  Rust bindings for the Python (CPython) interpreter
* `rust-cpython <https://github.com/dgrunwald/rust-cpython>`_:
  Rust <-> Python (CPython) bindings
* `RustPython <https://github.com/RustPython/RustPython>`_:
  A Python Interpreter written in Rust


Rejected Ideas
==============

Bet on HPy, leave the C API unchanged
-------------------------------------

The HPy project is developed outside CPython and so doesn't cause any
backward incompatibility in CPython. HPy API was designed with
efficiency in mind.

The problem is the long tail of C extensions on PyPI which are written
with the C API and will not be converted soon or will never be converted
to HPy. The transition from Python 2 to Python 3 showed that migrations
are very slow and never fully complete.

The PEP also rely on the assumption that `Most C extensions don't rely
directly on CPython internals`_.

The concept of HPy is not new: CPython has a limited C API which
provides a stable ABI since Python 3.4, see `PEP 384: Defining a Stable
ABI <https://www.python.org/dev/peps/pep-0384/>`_. Since it is an opt-in
option, most users simply use the **default** C API.


Prior Art
=========

* `pythoncapi.readthedocs.io <https://pythoncapi.readthedocs.io/>`_:
  Research project behind this PEP
* July 2019: Keynote `Python Performance: Past, Present, Future
  <https://github.com/vstinner/talks/raw/master/2019-EuroPython/python_performance.pdf>`_
  (slides) by Victor Stinner at EuroPython 2019
* [python-dev] `Make the stable API-ABI usable
  <https://mail.python.org/pipermail/python-dev/2017-November/150607.html>`_
  (November 2017) by Victor Stinner
* [python-ideas] `PEP: Hide implementation details in the C API
  <https://mail.python.org/pipermail/python-ideas/2017-July/046399.html>`_
  (July 2017) by Victor Stinner. Old PEP draft which proposed to add an
  option to build C extensions.
* `A New C API for CPython
  <https://vstinner.github.io/new-python-c-api.html>`_
  (Sept 2017) article by Victor Stinner
* `Python Performance
  <https://github.com/vstinner/conf/raw/master/2017-PyconUS/summit.pdf>`_
  (May 2017 at the Language Summit) by Victor Stinner:
  early discusssions on reorganizing header files, promoting PyPy, fix
  the C API, etc. Discussion summarized in `Keeping Python
  competitive <https://lwn.net/Articles/723949/>`_ article.


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
