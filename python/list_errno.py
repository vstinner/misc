#!/usr/bin/env python
import errno
import pprint
import os

err_names = [name for name in dir(errno) if name.startswith('E')]
err_list = [(getattr(errno, name), name) for name in err_names]
err_list.sort()
for err, name in err_list:
    text = os.strerror(err)
    print("% 3s: %s: %s" % (err, name, text))
