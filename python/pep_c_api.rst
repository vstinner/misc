PEP: xxx
Title: Unchain my heart
Version: $Revision$
Last-Modified: $Date$
Author: Victor Stinner <victor.stinner@gmail.com>,
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 31-May-2017


Abstract
========

Write a new A CPI with no implementation detail and use make C extensions use
this API by default. Add an opt-in option to compile C extensions with the full
API.


Rationale
=========

History of CPython forks
------------------------

Last 10 years, CPython was forked multiple times to try various attempts to
enhance CPython:

* Unladen Swallow: add a JIT compiler based on LLVM
* Pyston: add a JIT compiler based on LLVM (fork on CPython 2.7)
* Pyjion: add a JIT compiler based on Microsoft CLR
* Gilectomy: remove the Global Interpreter Lock nicknamed "GIL" (Gilles in
  french)
* etc.

Sadly, none is this project has been merged back into CPython. Unladen Swallow
looses its funding from Google, Pyston looses its funding from Dropbox, Pyjion
is developed in spare time of two Microsoft employees.

One hard technically issue which blocked these projects to really unleash their
power is the C API of CPython. Many old technical choices of CPython are
hardcoded in this API:

* reference counting
* garbage collector
* C structures like PyObject which contains headers for reference counting
  and the garbage collector
* specific memory allocators
* etc.

PyPy
----

PyPy uses more efficient structures and use a more efficient garbage collector
without reference counting. Thanks to that, PyPy succeeded to run Python code
up to 5x faster than CPython.


Copyright
=========

This document has been placed in the public domain.




..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:

