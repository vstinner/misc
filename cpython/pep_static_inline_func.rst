+++++++++++++++++++++++++++++++++++++++++
Convert macros to static inline functions
+++++++++++++++++++++++++++++++++++++++++

Advantages of static inline functions
=====================================

Developers must be extra careful to avoid every single macro pitfal. Even most
experienced C developers easily fall into these traps.

Well defined arguments type and return type
-------------------------------------------

In a static inline function, there is no need to cast arguments to a type,
since the arguments have a well defined type. Also, the return type is well
defined. There is no need to infer the type by reading carefully the code.

For backward compatibility, a macro is used to cast static inline function
arguments to continue accepting "any type" as ``PyObject*``.

Example of the ``Py_REFCNT()`` macro which casts to ``PyObject*``::

    #define Py_REFCNT(ob)           (((PyObject*)(ob))->ob_refcnt)

Inline the ``_Py_REFCNT()`` static inline function, there is no more need to
cast the argument::

    #define _PyObject_CAST_CONST(op) ((const PyObject*)(op))

    static inline Py_ssize_t _Py_REFCNT(const PyObject *ob) {
        return ob->ob_refcnt;
    }
    #define Py_REFCNT(ob) _Py_REFCNT(_PyObject_CAST_CONST(ob))

The ``Py_REFCNT()`` does the cast for backward compatibility.

More readable code
------------------

Macros are usually hard to read. For example, to execute multiple instructions
but return an expression, the ``expr1, expr2`` syntax must be used.

To respect operator precedence, macro arguments must be written between
parenthesis. It is common to have 3 levels of nested parenthesis. Example with
``(((``::

    #define DK_SIZE(dk) (((int64_t)1)<<DK_LOG_SIZE(dk))

If a macro contains multiple statements, ``do { ... } while (0)`` syntax
must be used. Otherwise, on the first statement would be conditional
in ``if (test) MACRO();``. Example::

    #define Py_SETREF(op, op2)                      \
        do {                                        \
            PyObject *_py_tmp = _PyObject_CAST(op); \
            (op) = (op2);                           \
            Py_DECREF(_py_tmp);                     \
        } while (0)

Example of the ``PyObject_INIT()`` macro::

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

Multiline code doesn't require ``\\`` continuation character. Regular C is
used: extra parenthesis are no longer needed.

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
there is no more need for ``_Py_COUNT_ALLOCS_COMMA``::

    static inline void _Py_NewReference(PyObject *op)
    {
        _Py_INC_TPALLOCS(op);
        Py_REFCNT(op) = 1;
    }

Python has many ``#ifdef`` options to support various build modes, especially
for debugging.

Variable scope
--------------

Variables declared in a static inline functions have a well defined scope: the
function, whereas variables declared in macros have the scope of the function
where the macro is used. Macros usually have to declare a local scope, like::

    ``#define MACRO() do { int local_variable = 1; ... } while (0)```.

Debugging and profiling
-----------------------

Compilers can emit debug information so debuggers and profilers can retrieve
the function name even when the function is inlined. Without that, it's way
harder to analyze a long function which inlines many sub-functions.

Moreover, it possible possible to put breakpoints on static inline functions
even when they are inlined!

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

No l-value issue
----------------

Many macros defined as expressions can be used to assign a value, even if it
was not intented behavior. Example::

    #define PyFloat_AS_DOUBLE(op) (((PyFloatObject *)(op))->ob_fval)

This macro can be used to modify an immutable object::

    PyFloat_AS_DOUBLE(num) = 1.0;

There is no compiler warning, it's valid code. Static inline functions cannot
be used as l-value::

    static inline double PyFloat_AS_DOUBLE(PyFloatObject *op)
    { return op->ob_fval; }

Using it in an assigment would raise a compiler error. It is possible to work
around the issue in the macro by adding a ``(void)`` cast::

    #define PyFloat_AS_DOUBLE(op) ((void)(((PyFloatObject *)(op))->ob_fval))

Expression leaking their result
-------------------------------

When writing a macro, it is easy to miss that an expression has a value which
can be used::

    #define PyList_SET_ITEM(op, i, v) (_PyList_CAST(op)->ob_item[i] = (v))

This macro was used incorrectly in third party C extensions (see `bpo-30459
<https://bugs.python.org/issue30459>`_), like::

    if (PyList_SET_ITEM (l, i, obj) < 0) { ... handle error ... }

This code compares ``obj < 0``: it checks if a pointer is negative, which is a
compiler error in C++. The macro was fixed to cast to ``void`` to remove the
expression value and also raise a compiler error with C compilers::

    #define PyList_SET_ITEM(op, i, v) ((void)(_PyList_CAST(op)->ob_item[i] = (v)))

By design, static inline functions don't have this issue.


Performance and inlining
========================

Static inline functions is a feature added to C99. In 2021, all C compilers are
able to inline them and use effecient heuristics for inlining.

When a C compiler decides to not inline, there is likely a good reason for
example. For example, inlining would reuse registers which require to
save/restore register values in the stack and so increase the stack memory
usage, or it would be less efficient.

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
it was decided to not force inlining. See discussion in the `bpo-35059
<https://bugs.python.org/issue35059>`_: "Convert Py_INCREF() and
PyObject_INIT() to inlined functions". The machine code was analyzed with
multiple C compilers and compiler options: ``Py_INCREF()`` was always inlined
without having to force inlining. The only case when it was not inlined was
debug builds, but this is acceptable for a debug build.

Prevent inlining
----------------

On the other side, the ``Py_NO_INLINE`` macro can be used to prevent inlining.
It is useful to reduce the stack memory usage, it is especially useful on
LTO+PGO builds which heavily inline code: see `bpo-33720
<https://bugs.python.org/issue33720>`_. This macro uses ``__attribute__
((noinline))`` with GCC and clang, and ``__declspec(noinline)`` with MSC.


Convert static inline functions to regular functions
====================================================

Converting macros to static inline functions fix the Python C API: define
function arguments type, result type, variable scope, etc.

This conversion also opens the ability later to convert static inline functions
to regular functions without changing the API. Regular functions can be used in
an embedded Python when macros and static inline functions cannot be used, for
example in programming languages other than C which don't support them, or when
Python is embedded only by loading symbols from libpython.

The impact on performance of these conversions should be measured. Performance
is a complex topic. Sometimes converting static inline functions to regular
functions can make these functions faster (see `PR #28893
<https://github.com/python/cpython/pull/28893>`_).


Discussions
===========

* `What to do with unsafe macros
  <https://discuss.python.org/t/what-to-do-with-unsafe-macros/7771>`_
  (March 2021)
* `[C-API] Convert obvious unsafe macros to static inline functions
  <https://bugs.python.org/issue43502>`_ (March 2021)
