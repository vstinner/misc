+++++++++++++++++++++++++++++++++++++++++
Convert macros to static inline functions
+++++++++++++++++++++++++++++++++++++++++

::

    PEP: xxx
    Title: Convert macros to static inline functions
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Content-Type: text/x-rst
    Created: 19-Oct-2021
    Python-Version: 3.11

Abstract
========

Convert macros to static inline funtions or regular functions to:

* Specify argument types and result type in the C API.
* Give access to regular functions to projects embedding Python which cannot
  use macros or static inline functions.


Rationale
=========

Developers must be extra careful to avoid every single macro pitfal. Even most
experienced C developers easily fall into these traps. Some issues are known
for years, while others have been discovered in the last years.

Converting macros to static inline functions and regular functions have many
advantages. The only concern is performance which is elaborated below.

Specify argument types and result type in the C API
---------------------------------------------------

In a static inline function, there is no need to cast arguments to a type,
since the arguments have a well defined type. Also, the return type is well
defined. There is no need to infer the result type by reading carefully the
macro code.

For backward compatibility, a macro is used to cast static inline function
arguments as ``PyObject*``, so the functions still accepts "any type".

Example of the ``Py_REFCNT()`` macro which casts to ``PyObject*``::

    #define Py_REFCNT(ob) (((PyObject*)(ob))->ob_refcnt)

Inside the ``_Py_REFCNT()`` static inline function, there is no more need to
cast the argument::

    #define _PyObject_CAST_CONST(op) ((const PyObject*)(op))

    static inline Py_ssize_t _Py_REFCNT(const PyObject *ob) {
        return ob->ob_refcnt;
    }
    #define Py_REFCNT(ob) _Py_REFCNT(_PyObject_CAST_CONST(ob))

The ``Py_REFCNT()`` macro does the cast for backward compatibility.

More readable code
------------------

Macros are usually hard to read. For example, to execute multiple instructions
but return an expression, the ``expr1, expr2`` syntax must be used.

To respect operator precedence, macro arguments must be written between
parenthesis. It is common to have 3 levels of nested parenthesis, if not more.
Example with ``(((``::

    #define DK_SIZE(dk) (((int64_t)1) << DK_LOG_SIZE(dk))

If a macro contains multiple statements, ``do { ... } while (0)`` syntax
must be used. Otherwise, ``if (test) MACRO();`` would unconditionally execute
following statements. Example formatted using the ``\\`` continuation
character::

    #define Py_SETREF(op, op2)                      \
        do {                                        \
            PyObject *_py_tmp = _PyObject_CAST(op); \
            (op) = (op2);                           \
            Py_DECREF(_py_tmp);                     \
        } while (0)

Example of the ``PyObject_INIT()`` macro using ``expr1, expr2, expr3`` syntax
to be an expression::

    #define PyObject_INIT(op, typeobj) \
        ( Py_TYPE(op) = (typeobj), _Py_NewReference((PyObject *)(op)), (op) )

Converted to a static inline function (simplified code)::

    static inline PyObject*
    _PyObject_INIT(PyObject *op, PyTypeObject *typeobj)
    {
        Py_TYPE(op) = typeobj;
        _Py_NewReference(op);
        return op;
    }

In a static inline function, the ``\\`` continuation character is no longer
needed. It is just plain regular C code. For example, extra parenthesis are
gone.

Easy usage of macros
--------------------

Using ``#ifdef`` inside a macro requires complicated code. Example with the
``_Py_NewReference()`` macro which required a ``_Py_COUNT_ALLOCS_COMMA`` macro
to handle ``#ifdef COUNT_ALLOCS``. Simplified code::

    #ifdef COUNT_ALLOCS
    #  define _Py_INC_TPALLOCS(OP) inc_count(Py_TYPE(OP))
    #  define _Py_COUNT_ALLOCS_COMMA  ,
    #else
    #  define _Py_INC_TPALLOCS(OP)
    #  define _Py_COUNT_ALLOCS_COMMA
    #endif /* COUNT_ALLOCS */

    #define _Py_NewReference(op) (                          \
        _Py_INC_TPALLOCS(op) _Py_COUNT_ALLOCS_COMMA         \
        Py_REFCNT(op) = 1)

Converting the macro to a static inline function made the code more readable,
``_Py_COUNT_ALLOCS_COMMA`` is gone::

    static inline void _Py_NewReference(PyObject *op)
    {
        _Py_INC_TPALLOCS(op);
        Py_REFCNT(op) = 1;
    }

Python has many ``#ifdef`` options to support various build modes, especially
for debugging.

Variable scope
--------------

Variables declared in a static inline functions have a well defined scope, the
function, whereas variables declared in macros inherit the scope of the
function where the macro is used by default. To work around this issue, macros
usually have to declare a local scope.

Example with the ``Py_SETREF()`` macro (simplified code)::

    #define Py_SETREF(op, op2)                      \
        do {                                        \
            PyObject *_py_tmp = _PyObject_CAST(op); \
            ...                                     \
        } while (0)

Debugging and profiling
-----------------------

Compilers can emit debug information so debuggers and profilers can retrieve
the function name when the function is inlined. Using macros, it's way more
complicated to analyze a long function which inlines many sub-functions.

Moreover, it possible possible to put breakpoints on static inline functions
even if they are inlined.

No side effect issue on macro arguments
---------------------------------------

Macros have an infamous issue with side effects on their arguments. Example::

    #define DOUBLE(x) ((x) + (x))
    int x = 1;
    int y = DOUBLE(++x);

The preprocessor produces::

    int x = 1;
    int y = ((++x) + (++x));
    // x = 3 and y = 6... or y = 5: this code has an undefined behavior!

The expected result would be ``x=2`` and ``y=4``. Static inline functions don't
have this issue::

    static inline int DOUBLE(int x) { return x + x; }
    int x = 1;
    int y = DOUBLE(++x);
    // x = 2 and y = 4: there is no undefined behavior

Unintended expression value in macros
-------------------------------------

When writing a macro, it is easy to miss that an expression has a value which
can be used::

    #define PyList_SET_ITEM(op, i, v) (_PyList_CAST(op)->ob_item[i] = (v))

This macro was used incorrectly in third party C extensions (see `bpo-30459
<https://bugs.python.org/issue30459>`_), like::

    if (PyList_SET_ITEM (l, i, obj) < 0) { ... handle error ... }

This code compares ``obj < 0``: it checks if a pointer is negative, which is a
compiler error in C++. The macro was fixed to cast the result to ``void``. So
the expression has no value and the faulty code also fails with a compiler
error with C compilers::

    #define PyList_SET_ITEM(op, i, v) ((void)(_PyList_CAST(op)->ob_item[i] = (v)))

The result type of a static inline functions is well defined, such API isuee is
easier to catch.


Performance and inlining
========================

Static inline functions is a feature added to C99. In 2021, C compilers can
inline them and have efficient heuristics to decide if a function should be
inlined or not.

When a C compiler decides to not inline, there is likely a good reason for
example. For example, inlining would reuse registers which require to
save/restore register values in the stack and so increase the stack memory
usage.

Debug mode
----------

When Python is built in debug mode, most compiler optimizations are disabled.
For example, Visual Studio disables inlining. Benchmarks must not be run on a
Python debug build, only on release build: using LTO and PGO is recommended for
reliable benchmarks. LTO and PGO helps a lot compilers to take better decisions
to inline functions or not.

Force inlining
--------------

If a developer is convinced to know better machine code than C compiler, which
is very unlikely, it is still possible to mark the function with the
``Py_ALWAYS_INLINE`` macro. This macro uses ``__attribute__((always_inline))``
with GCC and clang, and ``__forceinline`` with MSC.

So far, previous attempts to use ``Py_ALWAYS_INLINE`` didn't show any benefit
and were abandonned. See for example: `bpo-45094
<https://bugs.python.org/issue45094>`_: "Consider using ``__forceinline`` and
``__attribute__((always_inline))`` on static inline functions (``Py_INCREF``,
``Py_TYPE``) for debug builds".

When the ``Py_INCREF()`` macro was converted to a static inline functions in 2018
(`commit <https://github.com/python/cpython/commit/2aaf0c12041bcaadd7f2cc5a54450eefd7a6ff12>`__),
it was decided to not force inlining. The machine code was analyzed with
multiple C compilers and compiler options: ``Py_INCREF()`` was always inlined
without having to force inlining. The only case where it was not inlined was
debug builds, but this is acceptable for a debug build. See discussion in the
`bpo-35059 <https://bugs.python.org/issue35059>`_: "Convert Py_INCREF() and
PyObject_INIT() to inlined functions".

Prevent inlining
----------------

On the other side, the ``Py_NO_INLINE`` macro can be used to prevent inlining.
It is useful to reduce the stack memory usage, it is especially useful on
LTO+PGO builds which heavily inline code: see `bpo-33720
<https://bugs.python.org/issue33720>`_. This macro uses ``__attribute__
((noinline))`` with GCC and clang, and ``__declspec(noinline)`` with MSC.


Convert macros and static inline functions to regular functions
---------------------------------------------------------------

There are projects embedding Python or using Python which cannot use macros and
static inline functions. For example, projects using programming languages
other than C and C++. There are also projects written in C which make the
deliberate choice of only getting libpython symbols (functions and variables).

Converting macros and static inline functions to regular functions make these
functions accessible to these projects.


Specification
=============

Convert macros to static inline functions
-----------------------------------------

Most macros should be converted to static inline functions to prevent macro
pitfalls listed in the Rationale section.

Macros which can remain macros:

* Macro with no value. Example:: `#define Py_HAVE_CONDVAR``
* Macro defining a number. Example:: ``#define METH_VARARGS 0x0001``
* Compatibility layer for different C compilers, C extensions, or recent C
  features.
  Example:: ``#define Py_ALWAYS_INLINE __attribute__((always_inline))``.

Convert static inline functions to regular functions
----------------------------------------------------

Converting static inline functions to regular functions give access to these
functions for projects which cannot use macros and static inline functions.

The performance impact of such conversion should be measured with benchmarks.
If there is a significant slowdown, there should be a good reason to do the
conversion. A reason can be to hide implementation details.

Performance and C compiler optimizations is a complex topic. Sometimes
converting static inline functions to regular functions can make these
functions faster (see `PR #28893
<https://github.com/python/cpython/pull/28893>`_).

The internal C API exposes implemenation details by design. Using static inline
functions in the internal C API is reasonable.


Backwards Compatibility
=======================

Converting a macro implemented as an expession to a static inline function or a
function which has no return value (``void``) is an incomatible change made on
purpose to prevent misusing the C API and to detect bugs in C extensions.


Discussions
===========

* `What to do with unsafe macros
  <https://discuss.python.org/t/what-to-do-with-unsafe-macros/7771>`_
  (March 2021)
* `[C-API] Convert obvious unsafe macros to static inline functions
  <https://bugs.python.org/issue43502>`_ (March 2021)


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
