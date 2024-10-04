#!/usr/bin/env python3
import sys
import os.path
import re

def replace_regex(regs):
    version = regs[1]
    return f' ({version})'

regex = re.compile(r'-([0-9]+(?:\.[0-9]+)*)$')
filename = sys.argv[1]
projects = set()
with open(filename, encoding="utf8") as fp:
    for line in fp:
        line = line.rstrip()
        if not line:
            continue
        filename = line.split(':')[0]
        filename = os.path.basename(filename)
        filename = filename.removesuffix('.tar.gz')
        filename = filename.removesuffix('.zip')
        filename = regex.sub(replace_regex, filename)
        projects.add(filename)

print(f"Affected projects ({len(projects)}):")
for name in sorted(projects):
    print(f"* {name}")
