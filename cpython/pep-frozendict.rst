Headers::

    PEP: xxx
    Title: Add frozendict built-in type
    Author: Victor Stinner <vstinner@python.org>, Donghee Na <donghee.na@python.org>
    Status: Draft
    Type: Standards Track
    Created: 06-Nov-2025
    Python-Version: 3.15

Abstract
========

A new public immutable type ``frozendict`` is added to the ``builtins``
module.

We expect frozendict to be safe by design, as it prevents any unintended modifications.
This addition benefits not only CPython’s internal implementation but also third-party authors who can take advantage of a reliable,
immutable dictionary type.


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

* Using an immutable mapping as a function parameter default value
  avoids the problem of mutable default value.

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

The hash value does not depend on the items order. It is computed on
keys and values. Pseudo-code of ``hash(frozendict)``::

    hash(frozenset(frozendict.items()))

Equality test does not depend on the items order neither. Example::

    >>> a = frozendict(x=1, y=2)
    >>> b = frozendict(y=2, x=1)
    >>> hash(a) == hash(b)
    True
    >>> a == b
    True


Typing
------

It is possible to use the standard typing notation for frozendicts::

    m: frozendict[str, int] = frozendict(x=1)


Representation
--------------

``frozendict`` will not use a special syntax for its representation.
The ``repr()`` of a ``frozendict`` instance looks like this:

    >>> frozendict(x=1, y=2)
    frozendict({'x': 1, 'y': 2})


C API
-----

Exposing the C API will help authors of C extensions to support ``frozendict`` in 
their extensions when they need to support immutable containers to make thread-safe very easily.
It will be important since :pep:`779` was accepted, people need this for their migration.

Add the following APIs:

* ``PyFrozenDict_Type``
* ``PyFrozenDict_New(iterable)`` function
* ``PyFrozenDict_Check()`` macro
* ``PyFrozenDict_CheckExact()`` macro

Even if ``frozendict`` is not a ``dict`` subclass, it can be used with
``PyDict_GetItemRef()`` and similiar "PyDict_Get" functions.

Passing a ``frozendict`` to ``PyDict_SetItem()`` or ``PyDict_DelItem()``
fails with ``TypeError``.


Differences between dict and frozendict
=======================================

* ``dict`` has more methods than ``frozendict``:

  * ``__delitem__(key)``
  * ``__setitem__(key, value)``
  * ``clear()``
  * ``pop(key)``
  * ``popitem()``
  * ``setdefault(key, value)``
  * ``update(*args, **kwargs)``

* A ``frozendict`` can be hashed if keys and values can be hashed
  with ``hash(frozendict)``.


Possible Candidates for frozendict in Pure Python Modules
=======================================================================

We have identified several internal CPython source files where adopting frozendict can enhance safety 
and prevent unintended modifications by design.
We also believe that there are additional potential use cases beyond the ones listed below.
* Lib 
   - _collections_abc.py
   - opcode.py
   - _opcode_metadata.py
   - _pydatetime.py
   - _pydecimal.py
   - bdb.py
   - dataclsses.py
   - dis.py
   - email/headerregistry.py
   - enum.py
   - functools.py
   - gettext.py
   - imaplib.py
   - importlib/_bootstrap_external.py
   - json/decoder.py
   - json/encoder.py
   - json/tool.py
   - locale.py
   - opcode.py
   - optparse.py
   - platform.py
   - plistlib.py
   - pydoc_data/topics.py
   - ssl.py
   - stringprep.py
   - symtable.py
   - tarfile.py
   - token.py
   - tomllib/_parser.py
   - typing.py


Relationship to PEP 416 frozendict
==================================

Since 2012 (PEP 416), the Python ecosystem evolved:

* ``asyncio`` was added in 2014 (Python 3.4)
* Free Threading was added in 2024 (Python 3.13)
* ``concurrent.interpreters`` was added in 2025 (Python 3.14)

There are now more use cases to share immutable mappings.

``frozendict`` now preserves the insertion order, whereas PEP 416
``frozendict`` was unordered (as PEP 603 ``frozenmap``). ``frozendict``
relies on the ``dict`` implementation which preserves the insertion
order since Python 3.6.

The first motivation to add ``frozendict`` was to implement a sandbox
in Python. It's no longer the case in this PEP.

``types.MappingProxyType`` was added in 2012 (Python 3.3). This type is
not hashable and it's not possible to inherit from it. It's also easy to
retrieve the original dictionary which can be mutated, for example using
``gc.get_referents()``.


Relationship to PEP 603 frozenmap
=================================

``frozenmap`` has different properties than frozendict:

* ``frozenmap`` items are unordered, whereas ``frozendict`` preserves
  the insertion order.
* ``frozenmap`` has additional methods:

  * ``including(key, value)``
  * ``excluding(key)``
  * ``union(mapping=None, **kw)``

==========  =============  ==============
Complexity  ``frozenmap``  ``frozendict``
==========  =============  ==============
Lookup      O(log n)       O(1)
Copy        O(1)           O(n)
==========  =============  ==============


Reference Implementation
========================

* ``frozendict`` shares most of its code with the ``dict`` type.
* Add ``PyFrozenDictObject`` which inherits from ``PyDictObject`` and
  has an additional ``ma_hash`` member.


Thread Safety
=============
Once the ``frozendict`` is created, it is immutable and can be shared safely between threads without any synchronization.


Future Work
===========
We are also going to make ``frozendict`` to be more efficient in terms of memory usage and performance compare to ``dict`` in future.


Rejected Ideas
==============

Inherit from dict
-----------------

If ``frozendict`` inherits from ``dict``, it would become possible to
call ``dict`` methods to mutate an immutable ``frozendict``.  For
example, it would be possible to call ``dict.__setitem__(frozendict,
key, value)``.

It may be possible to prevent modifying ``frozendict`` using ``dict``
methods, but that would require to explicitly exclude ``frozendict``
which can affect ``dict`` performance. Also, there is a higher risk of
forgetting to exclude ``frozendict`` in some methods and so having
"holes" in the API.

If ``frozendict`` does not inherit from ``dict``, there is no such
issue.


New syntax for frozendict literals
----------------------------------

No new syntax is proposed for ``frozendict`` literals. Various syntaxes
have been discussed.

A new syntax can be added later if needed.


References
==========

* PEP 416 frozendict
* PEP 603 collections.frozenmap
* https://discuss.python.org/t/pep-603-adding-a-frozenmap-type-to-collections/2318
* https://discuss.python.org/t/pep-603-frozenmap-vs-my-frozendict/2473


Acknowledgements
================

This PEP is based on prior work from Yury Selivanov (PEP 603).


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
