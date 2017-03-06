#!/usr/bin/env python3
import pyreplace
import textwrap
import unittest
from unittest import mock


def format(text):
    return textwrap.dedent(text).strip()


class CreateRegexTests(unittest.TestCase):
    def check(self, pattern, expected_regex):
        pattern_regex, replace = pyreplace.create_regexs(pattern, '')
        self.assertEqual(pattern_regex, expected_regex)

    def test_string(self):
        self.check('hello', 'hello')

    def test_spaces(self):
        self.check('x = 1', r'x *\= *1')
        self.check('if x: pass', r'(?:if +|if(?=\())x\: *pass')
        self.check('1\\n2', '(?P<indent> *)1\n(?P=indent)2')
        self.check('1\\n    print()',
                   '(?P<indent> *)1\n(?P=indent)\ \ \ \ print\(\)')
        self.check('x    =   1', r'x *\= *1')

    def test_expr(self):
        with mock.patch('pyreplace.EXPR_REGEX', 'EXPR'):
            # <expr>
            self.check('x = <expr>',
                       r'x *\= *(?P<group1>EXPR)')

            # <expr< + <1>: test reference
            self.check('x = <expr> + <1>',
                       r'x *\= *(?P<group1>EXPR) *\+ *(?P=group1)')

    def test_regex(self):
        self.check('a<regex:.>b', r'a.b')


class ReplaceSourceTestCase(unittest.TestCase):
    def set_pyreplace(self, pattern, replace):
        pattern = format(pattern)
        replace = format(replace)

        self.replace = pyreplace.PyReplace([pattern, replace, 'test.py'])

    def check(self, source, expected):
        source = format(source)
        expected = format(expected)

        result = self.replace.replace_source(source)
        self.assertEqual(result, expected)

    def check_unchange(self, source):
        source = format(source)

        result = self.replace.replace_source(source)
        self.assertEqual(result, source)

    def test_string(self):
        self.set_pyreplace('abc', 'def')
        self.check('abc', 'def')

    def test_expr(self):
        self.set_pyreplace('x = <expr>', 'x = 3')
        self.check('x = 1', 'x = 3')
        self.check('x = "hello"', 'x = 3')
        self.check("x = 'hello'", 'x = 3')

    def test_expr_ref(self):
        self.set_pyreplace('x = <expr>', 'x = <1> + 1')
        self.check('x = y', 'x = y + 1')

        self.set_pyreplace('<expr> + <1>', '<1> * 2')
        self.check('x = y + y', 'x = y * 2')

    def test_space(self):
        self.set_pyreplace('x + y', 'x + y')
        self.check('x+y', 'x + y')
        self.check('x   +y', 'x + y')
        self.check('x+   y', 'x + y')
        self.check('x  +  y', 'x + y')

        # always followed by a space
        self.set_pyreplace('if x + y: pass', 'if x + y: pass')
        self.check('if x+y: pass', 'if x + y: pass')
        self.check_unchange('ifx+y: pass')

        # optional space if using parenthesis
        self.set_pyreplace('while <expr>: pass', 'while <1>: pass')
        self.check('while   0: pass', 'while 0: pass')
        self.check('while(0): pass', 'while (0): pass')
        self.check_unchange('while0: pass')

    def test_newline_indent(self):
        self.set_pyreplace('x = 1\nx = 2', 'ok')
        self.check('x = 1\nx = 2', 'ok')
        self.check('''
            if 1:
                x = 1
                x = 2
        ''', '''
            if 1:
                ok
        ''')

    def test_to_utf8(self):
        self.set_pyreplace("""
            if isinstance(<expr>, six.text_type):
                <1> = <1>.encode('utf-8')
        """, """
            <1> = encodeutils.to_utf8(<1>)
        """)

        self.check('''
            if isinstance(bla, six.text_type):
                bla = bla.encode('utf-8')
        ''', '''
            bla = encodeutils.to_utf8(bla)
        ''')

        self.check('''
            if 1:
                if isinstance(bla, six.text_type):
                    bla = bla.encode('utf-8')
        ''', '''
            if 1:
                bla = encodeutils.to_utf8(bla)
        ''')


if __name__ == "__main__":
    unittest.main()
