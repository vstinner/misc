Differences between dict and frozendict
=======================================

* ``dict`` has more methods than ``frozendict``:

  * ``__delitem__()``
  * ``__setitem__()``
  * ``clear()``
  * ``pop()``
  * ``popitem()``
  * ``setdefault()``

* ``frozendict`` can be hashed and support equality comparison
  (``frozendict1 == frozendict2``).


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

References
==========

* PEP 416 frozendict
* PEP 603 collections.frozenmap
* https://discuss.python.org/t/pep-603-adding-a-frozenmap-type-to-collections/2318
* https://discuss.python.org/t/pep-603-frozenmap-vs-my-frozendict/2473
