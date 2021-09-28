+++++++++++++++++++++++++++++++++++++++++
Taking the Python C API to the Next Level
+++++++++++++++++++++++++++++++++++++++++

C extensions are key in Python popularity
=========================================

The Python popularity comes from its great programming language but also
from its wide catalog of modules freely available on PyPI. Many of the
most popular Python modules rely directly or indirectly C extensions
written with the C API. The Python C API is a key component of the
Python popularity.

For example, the numpy project is now a common dependency on many
scientific projects and a large part of the project is written by hand
with the C API.

Abandonning or removing the C API is out of question. When PyPy only
supported a minority of C extensions, PyPy was less usable, and its C
API support was one of its main drawback. Today, the problem remains in
CPython when a new Python version doesn't support Cython or numpy, many
Python projects are not usable, especially during the development phase
of this next Python version.

Backward compatibility and unmaintained C extensions
====================================================

One important property of the C API is the backward compatibility.
Developers expect that if their C extension works on Python 3.10, it
will work unmodified in Python 3.11. Building the C extension with
Python 3.11 should be enough.

This property becomes very important for unmaintained C extensions.
Sometimes, it is just that the only maintainer is busy for a few months.
Sometimes, there is no activity for longer than 5 years.

When an incompatible change in introduced in the C API, like removing a
function or changing a function behavior changes, there is a risk of
breaking an unknown number of C extensions. If a C extension is
maintained, it is possible to submit a fix and wait for a release. The
situation becomes more complicated when the extension is unmaintained.

Forward compatibility and obtain the best possible performance
==============================================================

There are two main reasons for writing a C extension: implement a
function which cannot be written in pure Python, or write a C
accelerator: rewrite the 10% of an application in C where 90% of the CPU
time is spent. About the former use case, the intent is to obtain the
best possible performance. Tradeoffs are made with portability: it is
acceptable to only support a limited number of Python versions and to
only support a limited number of Python implementations (usually only
CPython).

Cython is a good example of accelerator. It is able to support a large
number of Python versions and multiple Python implementation with
compatibility layers and ``#ifdef``. The main drawback is that it is
common that Cython is broken by incompatible changes made at each Python
release. It happens because Cython relies to many implementation
details.

On the other side, the limited C API is a small as possible and excludes
implementation details on purpose. It provides a stable ABI. Building a
C extension only once produce a binary wheel package usable on many
Python versions. Each platform requires its own binary wheel package.

Emulating the current C API is inefficient
==========================================

The PyPy project is a Python implementation written from scratch: it was
not created as a fork of CPython. It made many implementation choices
different than CPython: no reference counting, moving garbage collector,
JIT compiler, etc.

To support C extensions, PyPy emulates the Python C API in its cpyext
module. When the C API tries to access an object, cpyext converts the
PyPy object to a CPython object (``PyObject``). CPython objects are less
efficient than PyPy objects for its JIT compiler and conversions from
PyPy objects to CPython objects is also inefficient. PyPy has to
reimplement every single detail of the CPython implementation to be as
much compatible as possible.

The C API exposes multiple implementation details:

* Reference counting, borrowed references, stealing references.
* Objects location in memory.
* Rely on pointers for object identity: Python 3.10 adds the ``Py_Is()``
  function to solve this problem.
* Expose the memory layout of Python objects as part of the API.
* Expose static types.
* Implicit execution context.
* etc.
