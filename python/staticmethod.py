#!/usr/bin/env python3
"""
Proof-of-concept tool to add a @staticmethod decorator and remove the first
parameter to functions of the list MODIFY_LINES.

Another tool is required to generate MODIFY_LINES. See for example this
patch for the hacking project (extension of flake8):
https://review.openstack.org/#/c/151952/

This tool requires redbaron:
https://github.com/Psycojoker/redbaron/

The tool requires redbaron 0.5.1 or newer.
"""
import redbaron
import tokenize
import json

with tokenize.open(__file__) as fp:
    content = fp.read()

class Foo:
    def method(self):
        print("bar")

def foo():
    print("foo")

# only modify Foo.method
MODIFY_LINES = [Foo.method.__code__.co_firstlineno]

red = redbaron.RedBaron(content)
for node in red.find_all('DefNode'):
    line_number = node.absolute_bounding_box.top_left.line
    if line_number not in MODIFY_LINES:
        continue
    node.decorators.append('@staticmethod')
    node.arguments.pop(0)
print(red.dumps(), end='')
