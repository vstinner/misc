Headers::

    PEP: xxx
    Title: Add frozendict built-in type
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Created: 06-Nov-2025
    Python-Version: 3.15

Abstract
========

A new public immutable type ``frozendict`` is added to the ``builtins``
module.


Rationale
=========

The proposed ``frozendict`` type:

* implements the ``collections.abc.Mapping`` protocol,
* supports pickling.

The following use cases illustrate why an immutable mapping is
desirable:

* Immutable mappings are hashable which allows their use as dictionary
  keys or set elements.

* This hashable property permits functions decorated with
  ``@functools.lru_cache()`` to accept immutable mappings as arguments.
  Unlike an immutable mapping, passing a plain dict to such a function
  results in error.

* Immutable mappings can be used to safely share dictionaries across
  thread and asynchronous task boundaries. The immutability makes it
  easier to reason about threads and asynchronous tasks.

There are already existing 3rd party ``frozendict`` and ``frozenmap``
available on PyPI, showing that there is a need for immutable mappings.


Specification
=============

A new public immutable type ``frozendict`` is added to the ``builtins``
module. It is not a ``dict`` subclass but inherits directly from
``object``.


Construction
------------

``frozendict`` implements a dict-like construction API:

* ``frozendict()`` creates a new empty immutable mapping;

* ``frozendict(**kwargs)`` creates a mapping from ``**kwargs``,
  e.g. ``frozendict(x=10, y=0, z=-1)``.

* ``frozendict(collection)`` creates a mapping from the passed
  collection object. The passed collection object can be:

  - a ``dict``,
  - another ``frozendict``,
  - an object with an ``items()`` method that is expected to return
    a series of key/value tuples,
  - or an iterable of key/value tuples.

The insertion order is preserved.


Iteration
---------

As ``frozendict`` implements the standard ``collections.abc.Mapping``
protocol, so all expected methods of iteration are supported::

    assert list(m.items()) == [('foo', 'bar')]
    assert list(m.keys()) == ['foo']
    assert list(m.values()) == ['bar']
    assert list(m) == ['foo']

Iteration in ``frozendict``, as in ``dict``, preserves the insertion
order.


Hashing
-------

``frozendict`` instances can be hashable just like tuple objects::

    hash(frozendict(foo='bar'))  # works
    hash(frozendict(foo=['a', 'b', 'c']))  # will throw an error

The hash value depends on the items order and is computes on keys and
values.


Typing
------

It is possible to use the standard typing notation for frozendicts::

    m: frozendict[str, int] = frozendict(x=1)


C API
-----

Even if ``frozendict`` is not a ``dict`` subclass, it can be used with
``PyDict_GetItemRef()`` and similiar "Get" functions.

Passing a ``frozendict`` to ``PyDict_SetItem()`` or ``PyDict_DelItem()``
do fail with ``TypeError``.

Add the following APIs:

* ``PyFrozenDict_Type``
* ``PyFrozenDict_Check()`` macro
* ``PyFrozenDict_CheckExact()`` macro


Differences between dict and frozendict
=======================================

* ``dict`` has more methods than ``frozendict``:

  * ``__delitem__()``
  * ``__setitem__()``
  * ``clear()``
  * ``pop()``
  * ``popitem()``
  * ``setdefault()``

* A ``frozendict`` can be hashed if keys and values can be hashed
  with ``hash(frozendict)``.


Relationship to PEP 416 frozendict
==================================

Since PEP 416, ``types.MappingProxyType`` was added to Python 3.3.

The rationale is different.


Relationship to PEP 603 frozenmap
=================================

frozenmap has different properties than frozendict:

* ``frozenmap`` items are unordered, whereas ``frozendict`` preserves
  the insertion order.
* ``frozenmap`` has additional methods:

  * ``including(key, value)``
  * ``excluding(key)``
  * ``union(mapping=None, **kw)``

==========  =============  ==============
Complexity  ``frozenmap``  ``frozendict``
==========  =============  ==============
Copy        O(1)           O(n)
Lookup      O(n)           O(1)
==========  =============  ==============


Reference Implementation
========================

* ``frozendict`` shares most of its code with the ``dict`` type.
* Add ``PyFrozenDictObject`` which inherits from ``PyDictObject`` and
  has an additional ``ma_hash`` member.


References
==========

* PEP 416 frozendict
* PEP 603 collections.frozenmap
* https://discuss.python.org/t/pep-603-adding-a-frozenmap-type-to-collections/2318
* https://discuss.python.org/t/pep-603-frozenmap-vs-my-frozendict/2473


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
