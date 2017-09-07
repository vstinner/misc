#!/usr/bin/env python3
import collections
import optparse
import re
import sys

# "378 tests OK."
TESTS_OK = re.compile('^[0-9]+ tests OK.$')

# "Timeout (1:00:00)!"
TIMEOUT = re.compile(r'^Timeout \([0-9:]+\)!$')

# "== CPython 3.5.0a2+ (default:b8ceb071159f, Mar 20 2015, 12:03:49) [GCC 4.8.2]"
TIMESTAMP = re.compile(r"CPython[^(]*\([^,]*, ([^)]*)\)")

FILENAME_REGEX = re.compile('([0-9]+)$')

KEEP_LAST_LINES = 20

# Strip \r for Windows buildbots
# Strip \0 because sometimes we get null bytes
STRIP_CHARS = "\n\r\t\0"


class Parser:
    def __init__(self, options):
        self.options = options
        self.success = True
        self.displaying_error = 0
        self.displaying_tb = False
        self.displaying_fatal_error = False
        self.buffered_lines = []
        self.tests_ok = False
        self.last_lines = collections.deque()
        self.empty_output = True
        self.line = None
        self.oneline = None
        self.timestamp = None
        self.test_started = False

    def flush_buffer(self):
        for line in self.buffered_lines:
            print(line.rstrip())
            self.empty_output = False
        self.buffered_lines.clear()

    def _display_line(self, line):
        print(line)

    def display_line(self, line=None, buffered=False):
        if self.options.oneline:
            return
        if line is None:
            if self.line is not None:
                line = self.line
            else:
                line = ''
        if not buffered:
            self.flush_buffer()
            self._display_line(line)
            self.empty_output = False
        else:
            self.buffered_lines.append(line)

    def parse_line(self, line):
        self.line = line

        if self.displaying_fatal_error:
            self.display_line()
        elif line.startswith('Fatal Python error: ') or TIMEOUT.match(line) or line == 'Killed':
            self.oneline = line
            self.display_line()
            self.displaying_fatal_error = True
        elif line.startswith('*** Error code '):
            self.display_line(buffered=True)

        elif line.startswith('== CPython '):
            self.test_started = True
            self.display_line(buffered=True)
            match = TIMESTAMP.search(line)
            if match:
                self.timestamp = match.group(1)
            else:
                self.timestamp = line
        elif TESTS_OK.match(line):
            if self.options.verbose:
                self.display_line()
            self.tests_ok = True
            self.oneline = line
        elif self.options.quiet:
            return

        elif self.displaying_error:
            if line == '----------------------------------------------------------------------':
                self.displaying_error += 1
                if self.displaying_error == 3:
                    self.displaying_error = 0
            elif self.options.verbose:
                self.display_line('| ' + line)
        elif line.startswith(('ERROR: ', 'FAIL: ')):
            self.display_line()
            self.success = False
            self.displaying_error = 1

        elif line.startswith('FAILED '):
            self.display_line()
            self.success = False

        elif self.displaying_tb:
            if line.startswith('  '):
                if self.options.verbose:
                    self.display_line()
            else:
                self.display_line()
                self.displaying_tb = False
                self.display_line('')
        elif 'Traceback ' in line:
            self.display_line()
            self.success = False
            self.displaying_tb = True

        else:
            self.last_lines.append(line)
            if len(self.last_lines) > KEEP_LAST_LINES:
                self.last_lines.popleft()

    def main(self, filename, show_filename):
        if show_filename or self.options.verbose:
            self.display_line("[ %s ]" % filename, buffered=True)

        with open(filename, errors='replace') as fp:
            for line in fp:
                line = line.strip(STRIP_CHARS)
                self.parse_line(line)
        self.line = None

        if self.options.verbose:
            self.flush_buffer()

        if (not self.tests_ok) and (not self.displaying_fatal_error):
            if not self.test_started:
                state = '<compilation error>'
            else:
                state = "<timeout?>"
            if not self.oneline:
                self.oneline = state

            if not self.options.oneline:
                self.flush_buffer()
                for line in self.last_lines:
                    self._display_line(line)
                self.display_line(state)
            self.success = False

        if show_filename and not self.empty_output:
            self.display_line()
            self.display_line()

        if self.options.oneline:
            if not self.oneline:
                self.oneline = '<unknown>'
            text = "%s: %s" % (filename, self.oneline)
            if self.timestamp:
                text += " (%s)" % self.timestamp
            print(text)

        return self.success


def parse_options():
    parser = optparse.OptionParser(usage="%prog [options] filename [filename2 ...]")
    parser.add_option("-v", "--verbose",
        help="Verbose mode",
        action="store_true", default=False)
    parser.add_option("-q", "--quiet",
        help="Quiet mode",
        action="store_true", default=False)
    parser.add_option("--oneline",
        help="One line mode",
        action="store_true", default=False)
    options, args = parser.parse_args()
    if not args:
        parser.print_help()
        exit(1)
    if options.quiet:
        options.verbose = False
    return options, args

def filename_key(filename):
    match = FILENAME_REGEX.match(filename)
    if match:
        number = int(match.group(1))
    else:
        number = 0
    return (number, filename)

def main():
    options, filenames = parse_options()
    filenames.sort(key=filename_key)
    show_filename = (len(filenames) > 1)
    success = True
    try:
        for filename in filenames:
            success &= Parser(options).main(filename, show_filename)
    except BrokenPipeError:
        sys.exit(1)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
