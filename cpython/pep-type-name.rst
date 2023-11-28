PEP: Unify type name formatting

Abstract
========

Change how type names are formatted in Python and C to no longer format
type names differently depending on how types are implemented. Add new
convenient API for that. Also, put an end to the cargo cult of
truncating type names in C.

Rationale
=========

Standard library
----------------

In the Python standard library, formatting a type name or the type name
of an object is a common operation to format an error message and to
implepment a ``__repr__()`` method. There are different ways to format a
type name which give different outputs.

In Python, ``type.__name__`` formats the type "short name", whereas
``f"{type.__module__}.{type.__qualname__}"`` formats the type "fully
qualified name. Usually, ``type(obj)`` or ``obj.__class__`` are used to
get the type of the object *obj*. Sometimes, the type name is put
between quotes.

Examples:

* ``raise TypeError("str expected, not %s" % type(value).__name__)``
* ``raise TypeError("can't serialize %s" % self.__class__.__name__)``
* ``name = "%s.%s" % (obj.__module__, obj.__qualname__)``

Qualified names were added to types (``type.__qualname__``) in Python
3.3 by `PEP 3155 – Qualified name for classes and functions
<https://peps.python.org/pep-3155/>`_.

In C, the most common way to format a type name is to get the
``PyTypeObject.tp_name`` member of the type. Example::

    PyErr_Format(PyExc_TypeError, "globals must be a dict, not %.100s",
                 Py_TYPE(globals)->tp_name);

The type qualified name (``type.__qualname__``) is only used at a single
place, by the ``type.__repr__()`` implementation. Using
``Py_TYPE(obj)->tp_name`` is more convenient than calling
``PyType_GetQualName()`` which requires ``Py_DECREF()``. Moreover,
``PyType_GetQualName()`` was only added recently, in Python 3.11.

Some functions use ``%R`` to format a type name. Example::

    PyErr_Format(PyExc_TypeError,
                 "calling %R should have returned an instance "
                 "of BaseException, not %R",
                 type, Py_TYPE(value));


Using PyTypeObject.tp_name is inconsistent
------------------------------------------

The ``PyTypeObject.tp_name`` member is different depending on the type
implementation:

* Static types and heap types in C: type fully qualified name (module
  qualified name and type qualified name)
* Python class: type short name (``type.__name__``).

So using ``Py_TYPE(obj)->tp_name`` to format an object type name gives
a different output depending if a type is implemented in C or in Python.

It goes against `PEP 399 – Pure Python/C Accelerator Module
Compatibility Requirements <https://peps.python.org/pep-0399/>`__
principles which require code to behave the same way if written in
Python or in C.

So the ``PyTypeObject.tp_name`` member should not be used to format a
type name.


Truncating type names in C
--------------------------

In 1998, when the ``PyErr_Format()`` function was added, the
implementation used a fixed buffer of 500 bytes. In 2001, it was
modified to allocate a dynamic buffer on the heap. Too late, the cargo
cult is to use ``"%.100s"`` format and nobody reminds why. In Python,
type names are not truncated.

Truncating type names in C but not in Python goes against `PEP 399 –
Pure Python/C Accelerator Module Compatibility Requirements
<https://peps.python.org/pep-0399/>`__ principles which require code to
behave the same way if written in Python or in C.

See the issue: `Replace %.100s by %s in PyErr_Format(): the arbitrary
limit of 500 bytes is outdated
<https://github.com/python/cpython/issues/55042>`__ (2011).


Specification
=============

* Add ``type.__fully_qualified_name__`` attribute.
* Add ``%T`` and ``%#T`` formats to ``PyUnicode_FromFormat()``.
* Add ``PyType_GetFullyQualifiedName()`` function.
* Recommend using the type short name format in error messages.
* Recommend using the type fully qualified name in ``repr()``.
* Recommend not truncating type names.

Python API
----------

Add ``type.__fully_qualified_name__`` read-only attribute, the fully
qualified name of a type: similar to
``f"{type.__module__}.{type.__qualname__}"`` or ``type.__qualname__`` if
``type.__module__`` is not a string or is equal to ``"builtins"``.

Add PyUnicode_FromFormat() formats
----------------------------------

Add ``%T`` and ``%#T`` formats to ``PyUnicode_FromFormat()`` to format
a type name:

* ``%T`` formats ``type.__name__``: the type "short name"
* ``%#T`` formats ``type.__fully_qualified_name__``: the type "fully
  qualified name".

The hash character (``#``) in the format string stands for
`alternative format
<https://docs.python.org/3/library/string.html#format-specification-mini-language>`_.
For example, ``f"{123:x}"`` returns ``'7b'`` and ``f"{123:#x}"`` returns
``'0x7b'`` (``#`` adds ``0x`` prefix).

Both formats expect a type object.

For example, the code::

    PyErr_Format(PyExc_TypeError,
                 "__format__ must return a str, not %.200s",
                 Py_TYPE(result)->tp_name);

can be replaced with::

    PyErr_Format(PyExc_TypeError,
                 "__format__ must return a str, not %T",
                 Py_TYPE(result));

Add PyType_GetFullyQualifiedName() function
-------------------------------------------

Add the ``PyType_GetFullyQualifiedName()`` function to get the fully
qualified name of a type (``type.__fully_qualified_name__``).

API::

    PyObject* PyType_GetFullyQualifiedName(PyTypeObject *type)

On success, return a new reference to the string. On error, raise an
exception and return ``NULL``.


Recommend using the type short name in error message
----------------------------------------------------

The type short name (``type.__name__``) is recommended to format error
messages displayed to users.

Example in Python::

    raise TypeError(f"cannot pickle {cls.__name__} object")

Example in C::

    PyErr_Format(PyExc_TypeError,
                 "__format__ must return a str, not %T",
                 Py_TYPE(result));

The type fully qualified name (``type.__fully_qualified_name__``) can be
used in error messages written in logs which are more likely to be read
by system administrators and developers than being read by users.

In general, the short name is enough to identify a type and is easier to
read by an user than the longer and more complicated fully qualified
name.


Recommend using the type fully qualified name in __repr__()
-----------------------------------------------------------

The type fully qualified name (``type.__fully_qualified_name__``) is
recommended to implemented a ``__repr__()`` method. The type can be
identified in a reliable way by its fully qualified name. There is less
risk of having two different types with the same fully qualified name,
than two types with the same short name (``type.__name__``).

Example in Python::

    def __repr__(self):
        return (f"<{self.__class__.__fully_qualified_name__}"
                f" at {id(self):#x}: value={self._value}>")

Recommend not truncating type names
-----------------------------------

Type names must not be truncated. For example, the ``"%.100s"`` format
should be avoided: use the ``"%s"`` format instead (or ``"%T`` and
``"%#T`` formats in C).


Out of the PEP scope
====================

Later, the ``__fully_qualified_name__`` attribute can be added to other
types:

* Coroutine
* Function
* Generator
* Method

But these changes are out of the scope of this PEP.

By the way, modules have no ``__qualname__`` attribute. A module name,
``module.__name__``, is already the fully qualified name.


Rejected Ideas
==============

Change str(type)
----------------

The ``type.__str__()`` method can be modified to format a type name
differently. For example, to format the fully qualified name.

The problem is that it's an incompatible change. For example, ``enum``,
``functools``, ``optparse``, ``pdb`` and ``xmlrpc.server`` modules of
the standard library have to be updated. And ``test_dataclasses``,
``test_descrtut`` and ``test_cmd_line_script`` have to be updated as
well.

See the `pull request: type(str) returns the fully qualified name
<https://github.com/python/cpython/pull/112129>`_.


Add !t formatter to get an object type in format()
--------------------------------------------------

Use ``f"{obj!t:T}"`` to format ``type(obj).__name__``.


Add formats to type.__format__()
--------------------------------

Proposed formats:

* ``f"{type(obj):z}"`` formats ``type(obj).__name__``.
* ``f"{type(obj):M.T}"`` formats ``type(obj).__fully_qualified_name__``.
* ``f"{type(obj):M:T}"`` formats ``type(obj).__fully_qualified_name__``
  using colon (``:``) separator.

Using short format (such as a single letter ``z``) requires to refer to
format documentation to understand how a type name is formatted, whereas
``type(obj).__name__`` is explicit.

The dot character (``.``) is already used for the "precision" in format
strings. The colon character (``:``) is already used to separated the
expression from the format specification. For example, ``f"{3.14:g}"``
uses ``g`` format which comes after ``:``. Usually, a format type is a
single format, such as ``g`` in ``f"{3.14:g}"``, not ``M.T`` or ``M:T``.
Reusing dot and colon characters for a different purpose can be
misleading and make the format parser more complicated.


Use colon separator in fully qualified name
-------------------------------------------

The colon (``:``) separator eliminates guesswork when you want to import
the name, see ``pkgutil.resolve_name()``. A type fully qualified name
can be formatted as ``f"{type.__module__}:{type.__qualname__}"``, or
``type.__qualname__`` if the module is ``"builtins"``.

In the standard library, no code formats a type fully qualified name
this way.

It is already tricky to get a type from its qualified name. The type
qualified name already uses the dot (``.``) separator between different
parts: class name, ``<locals>``, nested class name, etc.

The colon separator is not consistent with dot separator used in module
fully qualified name (``module.__name__``).


Other ways to format type names in C
------------------------------------

The ``PyUnicode_FromFormat()`` function supports multiple size
modifiers: ``hh`` (``char``), ``h`` (``short``), ``l``, ``ll``, ``z``,
``t``, ``j``.  The following length modifiers can be used to format a
type name:

* ``%hhT`` formats ``type.__name__``.
* ``%hT`` formats ``type.__qualname__``.
* ``%T`` formats ``type.__fully_qualified_name__``.

Other proposed formats:

* ``"%Q"``
* ``%lT`` formats ``type.__fully_qualified_name__``.

Having more formats to format type names can lead to inconsistencies
between different modules and make the API more error prone.

To format a type qualified name, ``f"{type.__qualname__}"`` can be used
in Python and ``PyType_GetQualName()`` can be used in C.


Pass an instance to %T format in C: omit Py_TYPE()
--------------------------------------------------

It was proposed to format a type name from a instance, like::

    PyErr_Format(..., "type %T", obj);

The intent is to avoid ``Py_TYPE()`` which returns a borrowed reference
to the type. Using a borrowed referencen can cause bug or crash if the
type is finalized or deallocated while being used.

In practice, it's unlikely that a type is finalized while the error
message is formatted. Instances of static types cannot see their type
being deallocated: static types are never deallocated. Instances of heap
types hold a strong reference to their type (in ``PyObject.ob_type``)
and it's safe to make the assumption that the code holds a strong
reference to the formatted object, so the object type cannot be
deallocated.

In short, using ``Py_TYPE(obj)`` to format an error message is safe.

If the ``%T`` format expects an instance, formatting a **type** name
cannot use ``%T`` format, whereas it's a common operation in extensions
of the standard library. So the ``%T`` format would only cover half of
cases. If the ``%T`` format takes a type, all cases are covered.


Other APIs to get a type fully qualified name
---------------------------------------------

* ``type.__fullyqualname__`` attribute
* Add a function to the ``inspect`` module


Omit __main__ in the type fully qualified name
----------------------------------------------

The ``pdb`` module formats a type fully qualified names in a similar way
than proposed ``type.__fully_qualified_name__`` but omits the module if
the module is equal to ``"__main__"``.

The ``unittest`` module formats a type fully qualified names the same
way than proposed ``type.__fully_qualified_name__``: only omits the
module if the module is equal to ``"builtins"``.



Discussions
===========

* Discourse: `Enhance type name formatting when raising an exception:
  add %T format in C, and add type.__fullyqualname__
  <https://discuss.python.org/t/enhance-type-name-formatting-when-raising-an-exception-add-t-format-in-c-and-add-type-fullyqualname/38129>`_
  (2023).
* Issue: `PyUnicode_FromFormat(): Add %T format to format the type name
  of an object <https://github.com/python/cpython/issues/111696>`_
  (2023).
* Issue: `C API: Investigate how the PyTypeObject members can be removed
  from the public C API
  <https://github.com/python/cpython/issues/105970>`_ (2023).
* python-dev thread: `bpo-34595: How to format a type name?
  <https://mail.python.org/archives/list/python-dev@python.org/thread/HKYUMTVHNBVB5LJNRMZ7TPUQKGKAERCJ/>`_
  (2018).
* Issue: `PyUnicode_FromFormat(): add %T format for an object type name
  <https://github.com/python/cpython/issues/78776>`_ (2018).
* Issue: `Replace %.100s by %s in PyErr_Format(): the arbitrary limit of
  500 bytes is outdated
  <https://github.com/python/cpython/issues/55042>`__ (2011).
