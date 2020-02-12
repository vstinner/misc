Subject: The future of Python is not CPython: may away from C API leaking implementation details

Hi,

To remain competitive in term of performance with other programming languages like Go or Rust, Python has to move away from its "legacy" CPython runtime. We can either promote other implementations like PyPy, evolve CPython implementation, or both.

Currently, PyPy can be found on python.org in Download > Alternative Python implementations, as the 3rd item of a list:
https://www.python.org/download/alternatives/

PyPy comes after IronPython and Jython in this list, whereas IronPython and Jython only support Python 2 which is no longer supported in CPython. PyPy now supports Python 3.6 (and Python 2.7).

Pure Python code runs fine on all Python implementations. The problem was always the same: C extensions which made the popular of Python. PyPy has cpyext which is less efficient than CPython, whereas PyPy is promoted as being more efficient than CPython.

Hiding implementation details from the C API of Python makes C extensions running way faster on PyPy. The HPy is concrete working example: ultrajson converted to the new C API "HPy" runs as fast as the origin C extension on CPython *but* it runs 4x faster on PyPy (compared to the original implementation using the current C API). 4x is a temporary milestone: you can expect better performance in the future if PyPy is optimized for HPy.

HPy is a new C API written from scratch to hide implementation details and to look close to the current C API to ease porting existing C extension. There is a plan to support HPy "output" when using Cython which would make existing Cython extension way more efficient on PyPy, with no impact on performance when running CPython.

HPy is a backward incompatible. Even when Cython will support HPy, there will still be plenty of existing C extension using directly the C API which we would try to continue to support. Another project is to evolve the limited C API to make it usable by way more C extensions. The limited C API allows to build a C extension once and use it on multiple Python versions thanks to a stable ABI. In short, all implementations details are hidden and objects can only be accessed through function calls. (XXX: not completely true: the fact that it is possible to represent Python objects as C immutable pointers IS an implementation detail which prevents to use a moving GC)

CPython and PyPy are two options, but we should be include other Python implementations on the design of these evolutions, like RustPython, and maybe also MicroPython.

There are different implementation details: structure layouts like PyObject or PyListObject, specific memory allocators, specific garbage collector, etc.

For example, Rust has a very different way to handle memory: there is a strong constraint on memory ownership. We should design an API which takes that in account to make it efficient to exchange data between Rust and Python. Some Mercurial C extensions are being rewritten in Rust for example.

What's the benefit for CPython? CPython performances are limited by these implementation details. We should experiment tagged pointers or a tracing garbage collector. I'm talking about changing CPython internals, but the C API would continue to use something like reference counting for C extension. HPy uses "handles" which can be duplicated and closed.

Resources:

* https://github.com/pyhandle/hpy : HPy project
* https://pythoncapi.readthedocs.io/ : longer rationale of flaws of the current C API and propositions for a new better C API
* https://github.com/PyO3/pyo3 : Rust bindings for Python

Talks, articles:

* https://morepypy.blogspot.com/2018/09/inside-cpyext-why-emulating-cpython-c.html : technical explanation of why emulating cpyext is so hard/slow in PyPy
* https://morepypy.blogspot.com/2019/12/hpy-kick-off-sprint-report.html : HPy kick-off sprint report
* https://github.com/vstinner/talks/raw/master/2019-EuroPython/python_performance.pdf : My keynote "Python Performance: Past, Present, Future" at EuroPython 2019 which also suggests to work on subinterpreters
* https://fosdem.org/2020/schedule/event/python2020_rust/ : "Boosting Python with Rust"  by Raphaël Gomès (FOSDEM 2020)

PyPy is organizing a sprint in March to work on PyPy and HPy in Switzerland, Feb 29 - March 8th 2020:
https://morepypy.blogspot.com/2020/01/leysin-winter-sprint-2020-feb-28-march.html
