PEP: PySequence_AsObjectArray() API

Abstract
========

Add ``PySequence_AsObjectArray()`` function to the C API.

Rationale
=========

The Python C API is tighly coupled to its implementation: it makes many
implicit assumptions about the Python implementation. For example,
``PyTuple_GET_ITEM()``, ``PyList_GET_ITEM()`` and
``PySequence_Fast_GET_ITEM()`` make the assumption that Python tuple and
list are implemented as arrays of Python objects (``PyObject**`` C
type).

PyPy can store a list of integers as an array of integers. Using these C
API on such object requires to box the integers as ``PyObject`` to fit
into these APIs.

Moreover, the API makes the assumption that the array and objects cannot
be moved in memory: their memory address is constant, they are pinned in
memory. Other Python implementations may want to implement moving
garbage collector to save memory, reduce memory fragmentation and have
better performance.

Proposition
===========

Add ``PySequence_AsObjectArray()`` function with the following
signature::

    int PySequence_AsObjectArray(
        PyObject *seq,
        PyObject ***array,
        Py_ssize_t *size,
        PyResource *res);

On success, it returns ``0``, set ``*array`` and ``*size``, and
initialized ``*res``. The caller must be call ``PyResource_Close()``
when it's done with the array.

On error, raise an exception and return ``-1``.

The ``PyResource`` API is proposed by PEP xxx.

This proposed function is a variant of the ``PySequence_Fast()``:

* ``seq = PySequence_Fast(obj)`` becomes
  ``PySequence_AsObjectArray(obj, &seq, &size, &res)``.
* ``PySequence_Fast_GET_ITEM(seq, index)`` becomes ``seq[index]``.
* ``PySequence_Fast_GET_SIZE(seq)`` becomes ``size``.
* ``Py_DECREF(seq)`` becomes ``PyResource_Close(&res)``.
