#!/usr/bin/env python3
import collections
import os
import subprocess

DATE = "2024-01-01"
BRANCH = 'main'

print("Statistics on the %s branch after %s" % (BRANCH, DATE))
print("cwd: %s" % os.getcwd())
proc = subprocess.run(['git', 'log', '--after=%s' % DATE, BRANCH],
                      stdout=subprocess.PIPE,
                      universal_newlines=True)
authors = collections.Counter()
for line in proc.stdout.splitlines():
    if line.startswith('Author: '):
        line = line[8:]
        name = line.split(' <')[0]
        authors[name] += 1
for name, commits in authors.most_common():
    if commits < 5:
        break
    print(commits, name)
