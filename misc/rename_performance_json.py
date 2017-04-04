#!/usr/bin/env python3
import os
for name in os.listdir():
    name2 = '%s (%s).%s' % (name[:10], name[24:36], name[37:])
    print("%s -> %s" % (name, name2))
    os.rename(name, name2)
