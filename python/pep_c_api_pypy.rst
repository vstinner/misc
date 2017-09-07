PyPy notes:

00:28 < arigato> the C API used to make tons of sense for CPython and definitely contributed to its popularity.  but it grew immensely since then, to the point
                 where it's a major pain for Python alternatives, and alternatives like Cython or cffi exist nowadays.  so..?

00:29 < arigato> cool.  let's deprecate the C API then

00:31 < simpson> haypo: I have a modest proposal: cffi everywhere, and *no* C API. Period. No more Cython, no more SWIG. While I recognize that this is zealous,
                 hopefully it indicates to you the breadth of opinions on the issue.

00:31 < mattip> haypro: the answer to supporting cython is definitely yes, pandas (a large consumer of cython) works on pypy

00:34 < pjenvey> you're going to have a long transition anyway, deprecating the C API doesn't mean it's going to be removed immediately (of course it won't) -- not
                 everything needs to be rewritten in cffi before next tuesday

00:36 < pjenvey> well there has to be a carrot, fijal proposed the carrot being "works on pypy, and works well"
00:36 < pjenvey> maybe that's not enough of a carrot
00:36 < haypo> pjenvey: i am not sure that pypy is a big enough carrot. otherwise, companies would already have invested money to do it
00:36 < fijal> haypo: I'm not sure either. But it's bigger than no carrot at all

00:21 < simpson> I mean, folks are not in agreement about exactly which features of the C API are drawbacks.
00:21 < simpson> Can I list Cython as a drawback, for example?
00:22 < fijal> haypo: so cython exists because python is slow
00:22 < fijal> it really would not make sense on a sane language

00:25 < fijal> haypo: it exists because slowness, but yeah, that too
00:26 < fijal> (cffi solves the latter quite well, as seen by the super wide adoption)

[Instagram]
00:39 < mattip> if the answer is numpy/pandas/cython, that all pretty much works these days
00:41 < arigato> ...in other words, "why doesn't instagram uses PyPy" is answered by "because of the C API that is a mess to support in pypy"...

PyUnicode_4BYTE_DATA

* Advantage for PyPy: allow to remove problematic APIs
  like PySequence_Fast_ITEMS()
00:18 < fijal> so maybe here is the actual proposal - list the APIs that pypy supports
    https://bitbucket.org/pypy/pypy/raw/py3.5/pypy/module/cpyext/stubs.py
    00:25 < arigato> the real list of unimplemented CPython 3.5 API is much longer

    bitbucket.org/pypy/pypy/raw/default/pypy/module/cpyext/stubs.py

* Remove the C API, stop using Cython or SWIG: convert all C extensions to cffi
* PyPy already implements macros as function calls
* PyObject** PySequence_Fast_ITEMS(ob) has to go
* Don't fix Py_INCREF/DECREF issue
* Deprecate finalizer API
* Deprecate Unicode API
* It's not possible to remove C API
23:18 < arigato> I don't quite believe that an incremental approach would work to eventually bring the CPython C API back to a sane complexity allowing free
                 experimentation
23:18 < arigato> any attempt to do that will just create a N+1'th way to do things
23:38 < fijal> maybe in 10 years it'll get somewhere?

23:51 < fijal> haypo: I don't believe having an opt-in API that does not go even half way is helping anyone
23:51 < fijal> it won't make our lives easier, people will generally not use it

23:53 < fijal> haypo: your examples won't work

23:54 < fijal> haypo: carrots - right now there are (mostly) 2 problems with C API
23:54 < fijal> one is called numpy the other is called cython

* Single ABI for CPython and PyPy? unlikely

00:39 < antocuni> arigato, fijal: IIRC, at some point we tried tagged pointers and we saw that there they brought no sensible speedup (but also no slowdown)


00:45 < arigato> haypo: that's because, to a large extend, there *are* no such changes
00:46 < arigato> you can deprecate stuff, which might stop being used in 10 years
00:46 < arigato> but that's about it
00:46 < haypo> arigato: yeah, cpython is a dead dinosaur, it's super slow to move :)
00:47 < arigato> that's not my point here
00:47 < arigato> my point is that you can't really make the C API much nicer to support in another implementation
00:48 < arigato> it's too low-level and tied to the implementation
00:48 < arigato> yes, and we don't really care about small changes, because they are at most a few hours of work for us

PyDict_Next issue: https://bitbucket.org/pypy/pypy/issues/2436/support-pybind11-in-conjunction-with-pypys

01:24 < fijal> haypo: right so you came to us to ask "how does it help pypy" and the answer is "it doesn't"
01:24 < fijal> if you want to limit C API to make optimizations, that's perfectly fine
01:25 < fijal> but has nothing to do with us

