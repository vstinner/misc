#!/usr/bin/env python
from __future__ import with_statement
import sys

def detect_encoding(filename):
    with open(filename, 'rb') as f:
        content = f.read()
    try:
        content.decode('ASCII')
    except UnicodeDecodeError:
        pass
    else:
        return 'ASCII'
    try:
        content.decode('UTF-8')
    except UnicodeDecodeError:
        pass
    else:
        return 'UTF-8'
    return None

def main():
    filenames = sys.argv[1:]
    if not filenames:
        print("usage: %s file1 [file2 ...]" % sys.argv[0])
        sys.exit(1)
    for filename in filenames:
        encoding = detect_encoding(filename)
        if not encoding:
            encoding = '<unknown>'
        print("%s: %s" % (filename, encoding))

if __name__ == "__main__":
    main()
