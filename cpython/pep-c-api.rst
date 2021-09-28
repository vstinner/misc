+++++++++++++++++++++++++++++++++++++++++
Taking the Python C API to the Next Level
+++++++++++++++++++++++++++++++++++++++++

While the C API is a key of the Python popularity, it causes multiple
subtle and complex issues. There are different ways to use the C API,
each usage has its own constraints, and some constraints are exclusive.
This document lists constraints but doesn't propose changes, it only
gives ideas to solve some issues.

C extensions are key of the Python popularity
=============================================

The Python popularity comes from its great programming language but also
from its wide catalog of modules freely available on PyPI. Many of the
most popular Python modules rely directly or indirectly on C extensions
written with the C API. The Python C API is a key component of the
Python popularity.

For example, the numpy project is now a common dependency on many
scientific projects and a large part of the project is written by hand
with the C API.

Abandonning or removing the C API is out of question. When PyPy only
supported a minority of C extensions, PyPy was less usable, and its
incomplete C API support was one of its main drawback. Today, the
problem remains in CPython when a new Python version doesn't support
Cython or numpy: many Python projects depending on them are not usable,
especially during the development phase of the next Python version.

Backward compatibility and unmaintained C extensions
====================================================

One important property of the C API is the backward compatibility.
Developers expect that if their C extension works on Python 3.10, it
will work unmodified in Python 3.11: building the C extension with
Python 3.11 should be enough.

This property is even more important for unmaintained C extensions.
Sometimes, unmaintained just means that the only maintainer is busy for
a few months. Sometimes, the project has no activity for longer than 5
years and it is unlikely that it is going to change soon.

When an incompatible change is introduced in the C API, like removing a
function or changing a function behavior, there is a risk of breaking an
unknown number of C extensions.

One option can be to update old C extensions when they are built on
recent Python versions, to adapt them to incompatible changes.

Migration plan for incompatible changes
=======================================

One practical way to minimize the number of broken projects is to
attempt to check in advance if an incompatible C API is going to break
popular C extensions. For broken C extensions, propose a fix and wait
until a new release includes the fix, before introducing the change in
Python.

There should be a sensible migration path for big C extensions (e.g.
numpy) when incompatible changes are introduced. Whenever possible, it
should be possible to write a single code base compatible with old and
new Python versions. A compatibility layer can be maintained externally.
Cython and numpy already have their own internal compatibility layer.

There should be a way to easily pick up common errors introduced by
migrating.

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
release. It happens because Cython relies on many implementation
details.

On the other side, the limited C API is a small as possible, excludes
implementation details on purpose, and provides a stable ABI. Building a
C extension with the limited C API only once produces a binary wheel
package usable on many Python versions, but each platform still requires
its own binary wheel package.

Emulating the current C API is inefficient
==========================================

The PyPy project is a Python implementation written from scratch, it was
not created as a CPython fork. It made many implementation choices
different than CPython: no reference counting, moving garbage collector,
JIT compiler, etc.

To support C extensions, PyPy emulates the Python C API in its cpyext
module. When the C API access an object, cpyext has to convert the PyPy
object to a CPython object (``PyObject``). CPython objects are less
efficient than PyPy objects with the PyPy JIT compiler and conversions
from PyPy objects to CPython objects are also inefficient. PyPy has to
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

The C API prevents optimizing CPython
=====================================

It is challenging to evolve the C API to optimize CPython without
breaking the backward compatibility or the forward compatibility.
Emulating the old C API is an option, but it is inefficient.

If everything above is achievable -- and we believe it is! -- we'll
arrive in a wonderful new future where Python implementations can
experiment with all sorts of amazing new features:

* tracing garbage collectors;
* nurseries for short-lived objects;
* sub-interpreters with separate contexts;
* specialised implementations of lists;
* removing the GIL;
* avoiding the boxing of primitive types;
* just-in-time compilation;
* ... and many other things you can imagine that we haven't!

No one can guarantee that a particular new idea will work out, but
exposing fewer implementation details via the C API will make it
possible to try many new things.
