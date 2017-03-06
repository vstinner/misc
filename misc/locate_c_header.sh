#!/bin/sh
pattern="$@"
options=-H
find /usr/include -name "*.h"|xargs grep $options "$pattern"
find /usr/lib/gcc -name "*.h"|xargs grep $options "$pattern"
