#!/usr/bin/python
"""
Remove ANSI escape sequences from stdin.

Usage:

    ./remove_ansi.py < text
"""
import re
import sys

REGEX = re.compile(r'\x1b\[(0m|3[0-9]m|1;3[0-9]m)', re.VERBOSE)

content = sys.stdin.read()
content = REGEX.sub('', content)
print(content)
