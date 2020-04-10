#!/usr/bin/env python3
"""
Replace a pattern in Python code.

Features:

* support <expr> in the pattern to match a Python expression, examples:

  - 123
  - 'string'
  - self.attr
  - obj[1]

* support <1> syntax in the pattern for back-reference
* support <1> syntax in the replacement string
* smart spaces: don't match the exact number of spaces, allow multiple
  spaces, but keep mandatoray after most keywords.
  For example, 'if x: pass' regex matchs 'if  x: pass' and 'if(0):pass'
  but not 'if0: pass'
* smart indentation: if a regex contains newlines, an indentation regex
  is inserted automatically
* support <regex:...> for inline regex: "a<regex:.>c" matches "abc" and "aXc"
  for example (regex dot "." match any character)

Examples:

* pyreplace.py 'x = <expr> + <expr>' 'x = <1> * 2'
  Replace 'x = y + y' with 'x = y * 2'
* pyreplace.py
      'PyObject_CallFunctionObjArgs(<expr>, <expr>, NULL)'
      'PyObject_CallFunctionObjArgs(<1>, &<2>)'
      Objects/listobject.c

"""
import keyword
import optparse
import os
import re
import sys
import tokenize


# 'identifier', 'var3', 'NameCamelCase'
IDENTIFIER_REGEX = r'[a-zA-Z_][a-zA-Z0-9_]*'
# '[0]'
GETITEM_REGEX = r'\[[^]]+\]'
# '()' or '(obj, {})', don't support nested calls: 'f(g())'
CALL_REGEX = r'\([^()]*\)'
# '[0]' or '(obj, {})' or '()[key]'
SUFFIX_REGEX = r'(?:%s|%s)' % (GETITEM_REGEX, CALL_REGEX)
# 'var' or 'var[0]' or 'func()' or 'func()[0]'
SUBEXPR_REGEX = r'%s(?:%s)*' % (IDENTIFIER_REGEX, SUFFIX_REGEX)
# '"hello"', "'hello'"
_QUOTE1_STRING_REGEX = r'"(?:[^"\\]|\\[tn"])*"'
_QUOTE2_STRING_REGEX = r"'(?:[^'\\]|\\[tn'])*'"
STRING_REGEX = r'(?:%s|%s)' % (_QUOTE1_STRING_REGEX, _QUOTE2_STRING_REGEX)
INT_REGX = '(?:[1-9][0-9]*|0)'
# 'inst', 'self.attr', 'self.attr[0]', '"str"', '123'
RAW_EXPR_REGEX = r'(?:%s(?:\.%s)*|%s|%s)' % (SUBEXPR_REGEX, SUBEXPR_REGEX, STRING_REGEX, INT_REGX)
# expr, (expr)
EXPR_REGEX = r'(?:%s|\(%s\))' % (RAW_EXPR_REGEX, RAW_EXPR_REGEX)
#EXPR_REGEX = r'(?:[^,]+?)'

OPTIONAL_SPACE = 'False None True break continue else finally pass try'.split()
# if a keyword is followed by a space in the regex, the space must be mandatory
# Example: "if x:" becomes "if +expr:", and not "if *expr:"
FOLLOWED_BY_SPACE = sorted(set(keyword.kwlist) - set(OPTIONAL_SPACE))


def _regex_pattern_ref(regs):
    return '(?P=group%s)' % regs.group(1)


def _regex_replace(regs):
    return '\\g<group%s>' % regs.group(1)


def escape_regex(pattern):
    pattern = pattern.replace('\\n', '\n')
    pattern = re.escape(pattern)
    return pattern

def create_regexs(pattern, replace):
    # escape regex characters
    parts = []
    pos = 0
    for match in re.finditer('<regex:(.*?)>', pattern):
        start = match.start(0)
        end = match.end(0)
        if start > pos:
            parts.append(escape_regex(pattern[pos:start]))
        parts.append(match.group(1))
        pos = end
    end = len(pattern)
    if end > pos:
        parts.append(escape_regex(pattern[pos:end]))
    pattern = ''.join(parts)

    # spaces
    pattern = re.sub(r'\\ ', ' *', pattern)
    pattern = re.sub(r'^((?: \*)+)',
                     lambda regs: r'\ ' * (len(regs.group(1)) // 2),
                     pattern, flags=re.MULTILINE)
    pattern = re.sub(r'(%s) \*' % '|'.join(FOLLOWED_BY_SPACE),
                     r'(?:\1 +|\1(?=\())',
                     pattern)
    pattern = re.sub(r'( \*)+',
                     r'[ \n]*',
                     pattern)

    # <expr>
    group_id = 0
    def replace_group(regs):
        nonlocal group_id
        group_id += 1
        return '(?P<group%s>%s)' % (group_id, EXPR_REGEX)

    pattern = re.sub(r'\<expr\>', replace_group, pattern)

    # reference <1>
    pattern = re.sub(r'\\<([0-9]+)\\>', _regex_pattern_ref, pattern)

    if '\\\n' in pattern:
        parts = pattern.split('\\\n')
        parts[0] = '(?P<indent> *)' + parts[0]
        for index in range(1, len(parts)):
            parts[index] = '(?P=indent)' + parts[index]
        pattern = '\n'.join(parts)

    replace = re.sub(r'\<([0-9]+)\>', _regex_replace, replace)
    if pattern.startswith('(?P<indent> *)'):
        replace = '\\g<indent>' + replace

    return (pattern, replace)


class PyReplace:
    def __init__(self, args=None):
        self.options, pattern, replace, self.paths = self.parse_options(args)
        pattern, self.replace = create_regexs(pattern, replace)
        self.pattern = re.compile(pattern, re.MULTILINE)

    @staticmethod
    def usage(parser):
        parser.print_help()
        print()
        program = sys.argv[0]
        print("usage: %s pattern replace path1 [path2 ...]" % program)
        print()
        print("- pattern can contain <expr> to match a Python expression")
        print("- replace can contain %N which contains matched Python expressions")
        print("- pathN can be a filename or a directory,")
        print("  directories and subdirectories are scanned for *.py files")
        print()
        print("Ex: %s unicode(<expr>) str(%%1) test.py" % program)
        sys.exit(1)

    @classmethod
    def parse_options(cls, args=None):
        parser = optparse.OptionParser(
            description=("pyreplace.py is a tool to replace a Python pattern with another"),
            usage="%prog [options] <operation> <file1> <file2> <...>")
        parser.add_option(
            '-c', '--to-stdout', action="store_true",
            help='Write output into stdout instead of modify files in-place '
                 '(imply --quiet option)')

        if args is None:
            args = sys.argv[1:]
        options, args = parser.parse_args(args)
        if len(args) < 3:
            cls.usage(parser)
            sys.exit(1)

        pattern = args[0]
        replace = args[1]
        paths = args[2:]

        return (options, pattern, replace, paths)

    def replace_source(self, source):
        return self.pattern.sub(self.replace, source)

    def replace_file(self, filename):
        with tokenize.open(filename) as fp:
            source = fp.read()

        source2 = self.replace_source(source)
        if source2 == source:
            return

        if self.options.to_stdout:
            print(source2, end='')
        else:
            print("Patch %s" % filename)

            with open(filename, "rb") as fp:
                encoding, _ = tokenize.detect_encoding(fp.readline)

            with open(filename, "w", encoding=encoding) as fp:
                fp.write(source2)

    def warning(self, message):
        print("WARNING: %s" % message)

    def _walk_dir(self, path):
        for dirpath, dirnames, filenames in os.walk(path):
            # Don't walk into .tox
            try:
                dirnames.remove(".tox")
            except ValueError:
                pass
            for filename in filenames:
                if filename.endswith(".py"):
                    yield os.path.join(dirpath, filename)

    def walk(self, paths):
        for path in paths:
            if os.path.isfile(path):
                yield path
            else:
                empty = True
                for filename in self._walk_dir(path):
                    yield filename
                    empty = False
                if empty:
                    if os.path.isdir(path):
                        self.warning("Directory %s doesn't contain any "
                                     ".py file" % path)
                        self.exitcode = 1
                    else:
                        self.warning("Path %s doesn't exist" % path)
                        self.exitcode = 1

    def main(self):
        for filename in self.walk(self.paths):
            try:
                self.replace_file(filename)
            except SyntaxError as exc:
                print("ignore %s: %s" % (filename, exc))


if __name__ == "__main__":
    PyReplace().main()
