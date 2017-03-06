#!/usr/bin/env python
"""
Benchmarking program implementing automatic calibration:

- compute the effictive resolution of the clock in Python
- compute the number of loops so the test takes at least 100 ms
- repeat a test at least 5 times
- try to not take more than 1 second to run a single benchmark, but it can
  take longer

Usage:

[--file FILE] timeit STMT
[--file FILE] timeit SETUP STMT
[--file FILE] script filename.py
show FILE
compare_to REFERENCE_FILE FILE2 FILE3 ...
compare FILE1 FILE2 ...
doctest

Options:

--verbose: Enable verbose mode
--debug: Enable debug mode
--min-time
--max-time
--min-repeat

Methods of the Application class to run a benchmark:

 * start_group("group name")
 * timeit(stmt, name=None)
 * timeit(stmt, setup, name=None)
 * bench_func(name, func, *args, **kw)
 * compare_functions([(name1, func1, args1), (name2, func2, args2), ...])

TODO:

- Repeat a test if the system load is higher than a threshold
"""
from __future__ import with_statement
import functools
import math
import os
import pickle
import platform
import re
import subprocess
import sys
import time
import timeit
try:
    # Python 3.4+
    from time import monotonic as timeout_timer, perf_counter
except ImportError:
    timeout_timer = time.time
    if sys.platform == "win32":
        perf_counter = time.clock
    else:
        perf_counter = time.time
try:
    from statistics import mean, stdev   # Python 3.4+
except ImportError:
    def mean(values):
        return float(sum(values)) / len(values)
    def stdev(values):
        # FIXME: implement it for Python < 3.4!
        return 'FIXME'
from optparse import OptionParser

# Python 2/3 compatibility
try:
    # Python 2
    xrange
    STRING_TYPES = basestring
except NameError:
    # Python 3
    xrange = range
    STRING_TYPES = str

COLOR_BETTER = "\033[42m%s\033[0m"
COLOR_WORSE = "\033[31m%s\033[0m"
UNSET = object()   # singleton

def get_cmd_output(*args):
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = process.communicate()
        return stdout.decode('ascii', 'replace')
    except:
        raise
        return None

def compute_timer_precision(timer):
    precision = None
    points = 0
    timeout = timeout_timer() + 1.0
    previous = timer()
    while timeout_timer() < timeout or points < 5:
        for loop in xrange(10):
            t1 = timer()
            t2 = timer()
            dt = t2 - t1
            if 0 < dt:
                break
        else:
            dt = t2 - previous
            if dt <= 0.0:
                continue
        if precision is not None:
            precision = min(precision, dt)
        else:
            precision = dt
        points += 1
        previous = timer()
    return precision

_FORMAT_DELTA = (
    # sec
    (100.0,    1, "%.0f sec", "%.0f sec +- %.0f sec"),
    (10.0,     1, "%.1f sec", "%.1f sec +- %.1f sec"),
    (1.0,      1, "%.2f sec", "%.2f sec +- %.2f sec"),
    # ms
    (100e-3, 1e3, "%.0f ms", "%.0f ms +- %.0f ms"),
    (10e-3,  1e3, "%.1f ms", "%.1f ms +- %.1f ms"),
    (1e-3,   1e3, "%.2f ms", "%.2f ms +- %.2f ms"),
    # us
    (100e-6, 1e6, "%.0f us", "%.0f us +- %.0f us"),
    (10e-6,  1e6, "%.1f us", "%.1f us +- %.1f us"),
    (1e-6,   1e6, "%.2f us", "%.2f us +- %.2f us"),
    # ns
    (100e-9, 1e9, "%.0f ns", "%.0f ns +- %.0f ns"),
    (10e-9,  1e9, "%.1f ns", "%.1f ns +- %.1f ns"),
    (1e-9,   1e9, "%.2f ns", "%.2f ns +- %.2f ns"),
)

def format_delta(dt, stdev=None):
    """
    >>> format_delta(1e-10)
    '0 ns'
    >>> format_delta(0.32e-6)
    '320 ns'
    >>> format_delta(3.2e-6)
    '3.2 us'
    >>> format_delta(32e-6)
    '32 us'
    >>> format_delta(320e-6)
    '320 us'
    >>> format_delta(1.0)
    '1 sec'
    >>> format_delta(1.2345)
    '1.23 sec'
    >>> format_delta(123.45)
    '123 sec'
    >>> format_delta(1234.56)
    '1235 sec'
    """

    for min_dt, factor, fmt, fmt_stdev in _FORMAT_DELTA:
        if dt >= min_dt:
            break

    if stdev is not None:
        return fmt_stdev % (dt * factor, stdev * factor)
    else:
        return fmt % (dt * factor,)

def normalize_text(text):
    r"""
    >>> normalize_text(' a  b c   ')
    'a b c'
    >>> normalize_text('a\rb\n\tc   ')
    'a b c'
    """
    text = str(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

_NOSET = object()

class PlatformInfoItem:
    def __init__(self, key, title, value):
        self.key = key
        self.title = title
        self.value = value

    def __repr__(self):
        return "%s=%r" % (self.key, self.value)

    def __str__(self):
        return "%s: %s" % (self.title, self.value)

class PlatformInfo:
    def __init__(self, data=None):
        if data is not None:
            self._items = data
        else:
            self._items = {}

    def __iter__(self):
        return iter(self._items.values())

    def get(self, key, default=None):
        item = self._items.get(key, None)
        if item is not None:
            return item.value
        else:
            return default

    def add(self, key, title, value):
        value = normalize_text(value)
        item = PlatformInfoItem(key, title, value)
        self._items[key] = item

    def collect_data(self, config):
        import datetime, struct
        date = str(datetime.datetime.now()).split('.', 1)[0]
        self.add('date', 'Date', date)
        self.add('platform', 'Platform', platform.platform())
        bits = [
            'int=%s' % (struct.calcsize('I')*8),
            'long=%s' % (struct.calcsize('L')*8),
        ]
        try:
            bits.append('long long=%s' % (struct.calcsize('Q')*8))
        except struct.error:
            pass
        try:
            import ctypes
            bits.append('size_t=%s' % (ctypes.sizeof(ctypes.c_size_t)*8))
        except ImportError:
            pass
        bits.append('void*=%s' % (struct.calcsize('P')*8))
        self.add('bits', 'Bits', ', '.join(bits))
        self.add('python_version', 'Python version', sys.version)
        if sys.hexversion < 0x3030000:
            if sys.maxunicode == 0xffff:
                unicode_impl = 'UTF-16'
            else:
                unicode_impl = 'UCS-4'
        else:
            unicode_impl = 'PEP 393'
        self.add('python_unicode', 'Python unicode implementation', unicode_impl)
        self.get_cpu_model()
        try:
            import sysconfig
            cflags = sysconfig.get_config_var('CFLAGS')
            self.add('cflags', 'CFLAGS', cflags)
        except ImportError:
            pass
        self.read_scm()

        import time
        if config.timer is time.time:
            timer_name = 'time'
        elif config.timer is time.clock:
            timer_name = 'clock'
        elif hasattr(time, 'perf_counter') and config.timer is time.perf_counter:
            timer_name = 'perf_counter'
        elif hasattr(time, 'monotonic') and config.timer is time.monotonic:
            timer_name = 'monotonic'
        else:
            timer_name = None
        if timer_name:
            if hasattr(time, 'get_clock_info'):
                try:
                    clock_info = time.get_clock_info(timer_name)
                except ValueError:
                    pass
                else:
                    self.add('timer_info', 'Timer info', str(clock_info))
            self.add('timer', 'Timer', 'time.%s' % timer_name)
        else:
            self.add('timer', 'Timer', str(config.timer))

        precision = config.get_timer_precision()
        self.add('timer_precision', 'Timer precision', format_delta(precision))

    def get_cpu_model(self):
        try:
            cpuinfo = open("/proc/cpuinfo")
        except IOError:
            return
        with cpuinfo:
            for line in cpuinfo:
                if line.startswith('model name'):
                    model = line.split(':', 1)[-1]
                    self.add('cpu_model', 'CPU model', model)
                    return

    def read_scm(self):
        srcdir = os.curdir

        revision = get_cmd_output('hg', 'id', '-i', srcdir)
        if not revision:
            return
        revision = normalize_text(revision)
        mercurial = ['hg', 'revision=%s' % revision]

        tag = get_cmd_output('hg', 'id', '-t', srcdir)
        tag = normalize_text(tag)
        if tag:
            mercurial.append('tag=%s' % tag)

        branch = get_cmd_output('hg', 'id', '-b', srcdir)
        branch = normalize_text(branch)
        if branch:
            mercurial.append('branch=%s' % branch)

        date = get_cmd_output('hg', 'log', '-r', revision.rstrip('+'), '--template="{date|isodate}"')
        date = normalize_text(date)
        if date:
            mercurial.append('date=%s' % date)

        self.add('scm', 'SCM', ' '.join(mercurial))

    def display_all(self, options):
        for item in self:
            if options.debug:
                print(repr(item))
            else:
                print(str(item))
        print("")

    def export(self):
        data = []
        for item in self:
            data.append((item.key, item.title, item.value))
        return data

    @classmethod
    def load(cls, data):
        platform_info = cls(data={})
        for key, title, value in data:
            platform_info.add(key, title, value)
        return platform_info

class BenchmarkResult:
    def __init__(self, name=''):
        self.name = name
        self.results = []
        self._avg = UNSET
        self._stdev = UNSET

    def __repr__(self):
        avg = self.format_avg()
        return '<BenchmarkResult name=%r avg=%s>' % (self.name, avg)

    def add(self, dt, loops=1):
        dt = float(dt) / loops
        self.results.append(dt)
        self._avg = UNSET
        self._stdev = UNSET

    @property
    def avg(self):
        if self._avg is UNSET:
            self._avg = mean(self.results)
        return self._avg

    @property
    def stdev(self):
        if self._stdev is UNSET:
            if len(self.results) >= 2:
                self._stdev = stdev(self.results)
            else:
                self._stdev = None
        return self._stdev

    def format_avg(self, options=None, verbose=None, reference=None, name=True, color=False):
        if options is not None:
            debug = options.debug
            if verbose is None:
                verbose = options.verbose
        else:
            debug = None
            if verbose is None:
                verbose = False
        if not self.results:
            raise ValueError("empty result")
        text = format_delta(self.avg, self.stdev)
        format_color = None
        if reference is not None:
            if reference is not self and reference.avg != 0:
                percent = (self.avg - reference.avg) * 100.0 / reference.avg
                if abs(percent) >= 5.0:
                    if percent > 0:
                        format_color = COLOR_WORSE
                    else:
                        format_color = COLOR_BETTER
                    if verbose:
                        if percent > 0:
                            percent = "%.0f%% slower" % percent
                        else:
                            percent = "%.0f%% faster" % (-percent)
                    else:
                        percent = "%+.0f%%" % percent
                    comment = percent
                    text += " (%s)" % comment
            else:
                text += " (*)"
        if name:
            text = "%s: %s" % (text, self.name)
        if verbose:
            text += (" (min=%s, max=%s)"
                     % (format_delta(min(self.results)),
                        format_delta(max(self.results))))
        if debug:
            text += " (%s points)" % len(self.results)
        if color:
            return (text, format_color)
        else:
            return text

    @staticmethod
    def sort_key_func(result):
        return result.avg

    def export(self):
        return { 'name': self.name, 'results': self.results}

    @classmethod
    def load(cls, data):
        result = cls(data['name'])
        result.results = data['results']
        return result

class BenchmarkConfig:
    def __init__(self, application):
        self.verbose = application.options.verbose
        self.timer = perf_counter
        if application.options.debug:
            self._timer_precision = 1e-9
        else:
            self._timer_precision = None
        self.min_time = application.options.min_time
        self.max_time = application.options.max_time
        self.min_repeat = max(application.options.min_repeat, 1)
        self.use_color = sys.stdout.isatty() and os.name != "nt"

    def get_timer_precision(self):
        if self._timer_precision is None:
            self._timer_precision = compute_timer_precision(self.timer)
            if self.verbose:
                print("Timer precision = %s" % format_delta(self._timer_precision))
        return self._timer_precision

class BenchmarkRunner:
    def __init__(self, application, campaign, name=None):
        self.config = application.config
        self.options = application.options
        self.verbose = application.options.verbose
        self.campaign = campaign
        self.last_message = time.time()
        self.name = name

    def repeat(self, loops):
        raise NotImplementedError()

    def calibrate_timer(self):
        # Calibrate the number of loops
        if self.config.min_time < 1.0:
            timer_precision = self.config.get_timer_precision()
            min_time = max(self.config.min_time, timer_precision * 100)
            min_time_estimate = timer_precision * 10
        else:
            min_time = self.config.min_time
            min_time_estimate = self.config.min_time / 100

        if self.verbose:
            print("Calibrate the number of loops: min_time=%s"
                  % (format_delta(min_time),))

        loops = 1
        estimate = False
        min_progress = 1.0
        while True:
            dt = self.repeat(loops)

            if self.verbose:
                print("Calibrate the number of loops: %s for %s loops"
                      % (format_delta(dt), loops))

            if dt / min_time >= min_progress:
                break

            if dt >= min_time_estimate:
                # coarse estimation of the number of loops
                estimate = True
                old = loops
                loops = max(int(min_time * loops / dt), loops * 2)
                if self.verbose:
                    print("Calibrate the number of loops: estimate %s loops" % loops)
                min_progress = 0.75
            else:
                loops *= 10
        return dt, loops

    def run_benchmark(self):
        if self.options.keyword and self.options.keyword not in self.name:
            if self.verbose:
                print("Skip test: %s" % self.name)
            return

        result = BenchmarkResult(self.name)
        if self.verbose:
            print("Benchmark %r in progress..." % (self.name,))

        if not self.options.debug:
            dt, loops = self.calibrate_timer()
            result.add(dt, loops)

            # Choose how many time we must repeat the test
            repeat = int(math.ceil(self.config.max_time / dt))
            repeat = max(repeat, self.config.min_repeat)
            if 1 < repeat:
                # Repeat the benchmark
                progress = 0.0
                for index in xrange(repeat):
                    dt = self.repeat(loops)
                    result.add(dt, loops)
                    if self.verbose and 1.0 <= time.time() - self.last_message:
                        progress = float(1 + index) / repeat
                        self.display_progress(progress, result)
                display_last_progress = (progress != 1.0)
            else:
                display_last_progress = True
        else:
            dt = self.repeat(1)
            result.add(dt, 1)
            display_last_progress = True

        if self.verbose:
            if display_last_progress:
                self.display_progress(1.0, result)
        else:
            print(result.format_avg(self.options, verbose=True))
        self.campaign.add_result(result)
        return result

    def display_progress(self, progress, result):
        self.last_message = time.time()
        print("[%3.0f%%] %s" % (progress * 100, result.format_avg(self.options, verbose=True)))

class TimeitRunner(BenchmarkRunner):
    def __init__(self, application, campaign, name, stmt, setup, globals=None):
        if stmt is None:
            stmt = 'pass'
        if not name:
            if not isinstance(stmt, STRING_TYPES):
                name = stmt.__name__
            else:
                name = stmt
            name = normalize_text(name)
            if setup is not None:
                setup_text = normalize_text(setup)
                if not setup_text.endswith(';'):
                    setup_text += ';'
                name = "%s %s" % (setup_text, name)
        if not setup:
            setup = 'pass'
        BenchmarkRunner.__init__(self, application, campaign, name)
        if globals is not None:
            self.timer = timeit.Timer(stmt=stmt,
                                      setup=setup,
                                      timer=self.config.timer,
                                      globals=globals)
        else:
            self.timer = timeit.Timer(stmt=stmt,
                                      setup=setup,
                                      timer=self.config.timer)

    def repeat(self, loops):
        return self.timer.timeit(loops)

class FunctionRunner(BenchmarkRunner):
    def __init__(self, application, campaign, name, func):
        if not name:
            raise ValueError("empty name")
        BenchmarkRunner.__init__(self, application, campaign, name)
        self.func = func

    def repeat(self, loops):
        func = self.func
        loops_range = xrange(loops)
        start = perf_counter()
        for index in loops_range:
            func()
        end = perf_counter()
        return end - start

class Group:
    def __init__(self, application, name, results=None):
        if not name:
            raise ValueError("Empty name")
        self.options = application.options
        self.name = name
        if results is not None:
            self.results = results
        else:
            self.results = []
        self.total = None

    def __repr__(self):
        return '<Group name=%r results#=%s>' % (self.name, len(self.results))

    def get_result(self, name):
        for result in self.results:
            if result.name == name:
                return result
        return None

    def compute_total(self):
        if self.total is None:
            self.total = sum(result.avg for result in self.results)
        result = BenchmarkResult('Total')
        result.add(self.total)
        return result

    def add_result(self, result):
        if self.get_result(result.name) is not None:
            raise ValueError("Duplicate result: %s" % result.name)
        self.results.append(result)
        self.total = None

    def export(self):
        if not self.results:
            raise ValueError("empty group")
        results = [result.export() for result in self.results]
        return {'name': self.name, 'results': results}

    @classmethod
    def load(cls, application, data):
        results = [BenchmarkResult.load(result) for result in data['results']]
        keyword = application.options.keyword
        if keyword:
            results = [
                result
                for result in results
                if keyword in result.name]
        return cls(application, data['name'], results)

    def display_results(self):
        if self.name:
            print("=== %s ===" % self.name)
        for result in self.results:
            print(result.format_avg(self.options))

    def compare_results(self):
        if 1 < len(self.results):
            print("Results:")
            self.results.sort(key=BenchmarkResult.sort_key_func)
        else:
            print("Result:")
        for index, result in enumerate(self.results):
            if index == 0:
                reference = result
                text = result.format_avg(self.options)
            else:
                text = result.format_avg(self.options, reference=reference)
            print(text)
        print("")


class Campaign:
    def __init__(self, application=None, name=None, data=None):
        self.application = application
        if data is not None:
            self.name = data['name']
            self.platform_info = PlatformInfo.load(data['platform_info'])
            self.groups = [Group.load(application, group) for group in data['groups']]
            self.current_group = self.groups[-1]
        else:
            self.name = name
            self.platform_info = application.platform_info
            # group name => Group object
            self.groups = []
            self.current_group = None
        self._display_results = True
        self.options = application.options

    def get_group(self, name):
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def start_group(self, name):
        if (self.current_group is None) or (self.current_group.name != ""):
            if self.get_group(name) is not None:
                raise ValueError("Duplicate group: %s" % name)
            self.current_group = Group(self, name)
            self.groups.append(self.current_group)
        else:
            self.current_group.name = name

    def compare_each_group(self):
        if not self._display_results:
            return
        self._display_results = False
        for group in self.groups:
            group.compare_results()

    def display_results(self):
        if not self._display_results:
            return
        self._display_results = False
        print("Results:")
        for group in self.groups:
            if group.results:
                group.display_results()

    def add_result(self, result):
        if self.current_group is None:
            self.current_group = Group(self.application, 'Tests')
            self.groups.append(self.current_group)
        self.current_group.add_result(result)
        self._display_results = True

    def export(self):
        if not self.groups:
            raise ValueError("empty campaign (no group)")
        groups = [group.export() for group in self.groups if group.results]
        return {
            'name': self.name,
            'platform_info': self.platform_info.export(),
            'groups': groups,
        }


class ResultTable:
    EMPTY_CELL = '---'

    def __init__(self, options, config):
        self.lines = []
        self.has_total = False
        self.options = options
        self.color = config.use_color
        self.fillchar = ' '

    def add_line(self, columns):
        self.lines.append(columns)

    def add_results(self, name, results, first_is_reference):
        reference = results[0]
        if not first_is_reference:
            for result in results[1:]:
                if result is not None and result.avg < reference.avg:
                    reference = result

        columns = [name]
        for result in results:
            if result is not None:
                cell = result.format_avg(self.options,
                                         reference=reference,
                                         name=False,
                                         color=self.color)
                # cell is (text, format_color) if self.color is True
                columns.append(cell)
            else:
                columns.append(self.EMPTY_CELL)
        self.add_line(columns)

    def display_table(self):
        verbose = self.options.verbose
        widths = []
        for index in xrange(len(self.lines[0])):
            cells = (columns[index] for columns in self.lines)
            cells = (cell[0] if isinstance(cell, tuple) else cell for cell in cells)
            width = max(map(len, cells))
            widths.append(width)
        for line_number, columns in enumerate(self.lines):
            name = columns[0].ljust(widths[0], self.fillchar)
            if line_number == 0 and verbose:
                linechar = '='
            else:
                linechar = '-'
            cornerchar = '+'
            if verbose:
                text = ['| ' + name]
                line = [cornerchar + linechar * (1 + len(name))]
            else:
                text = [name]
                line = [linechar * len(name)]
            for index, cell in enumerate(columns[1:]):
                if isinstance(cell, tuple):
                    format_color = cell[1]
                    cell = cell[0]
                else:
                    format_color = None
                width = widths[1+index]
                text.append(' | ')
                line.append(linechar + cornerchar + linechar)
                cell = cell.rjust(width, self.fillchar)
                if format_color is not None:
                    cell = format_color % cell
                text.append(cell)
                line.append(linechar * (width))
                if verbose and index+2 == len(columns):
                    text.append(' |')
                    line.append(linechar + cornerchar)
            text = ''.join(text)
            line = ''.join(line)

            if line_number == 0:
                print(line)
            elif (line_number == len(self.lines)-1 and self.has_total) and not verbose:
                print(line)
            print(text)
            if verbose:
                print(line)
            elif line_number == 0 or line_number == len(self.lines)-1:
                print(line)
        print("")


class CampaignsTable:
    def __init__(self, application, campaigns):
        self.options = application.options
        self.config = application.config
        self.campaigns = campaigns

    def result_lists(self, dt_results):
        results = []
        for dt in dt_results:
            if dt is not None:
                result = BenchmarkResult()
                result.add(dt)
            else:
                result = None
            results.append(result)
        return results

    def display_platforms(self):
        same = set()
        first_campaign = self.campaigns[0]
        other_campaigns = self.campaigns[1:]
        output = False
        for item in first_campaign.platform_info:
            if any(campaign.platform_info.get(item.key, None) != item.value
                   for campaign in other_campaigns):
                continue
            if not output:
                print("Common platform:")
                output = True
            same.add(item.key)
            print(str(item))
        if output:
            print("")
        for campaign in self.campaigns:
            output = False
            for item in campaign.platform_info:
                if item.key in same:
                    continue
                if not output:
                    print("Platform of campaign %s:" % campaign.name)
                    output = True
                if self.options.debug:
                    print(repr(item))
                else:
                    print(str(item))
            if output:
                print("")

    def display(self, first_is_reference):
        self.display_platforms()

        first_campaign_groups = self.campaigns[0].groups

        if len(first_campaign_groups) > 1:
            totals_table = ResultTable(self.options, self.config)
            columns = ['Summary']
            for campaign in self.campaigns:
                columns.append(campaign.name)
            totals_table.add_line(columns)
            all_totals = [0.0] * len(self.campaigns)
        else:
            totals_table = None
            all_totals = None
        for first_group in first_campaign_groups:
            table = ResultTable(self.options, self.config)
            if first_group.name:
                columns = [first_group.name]
            else:
                columns = ['Tests']
            for campaign in self.campaigns:
                columns.append(campaign.name)
            table.add_line(columns)

            other_groups = [
                campaign.get_group(first_group.name)
                for campaign in self.campaigns[1:]]
            all_groups = [first_group] + other_groups
            totals = [0.0] * len(self.campaigns)
            for result in first_group.results:
                results = [result]
                totals[0] += result.avg
                reference = result
                for index, group in enumerate(other_groups):
                    if group is not None:
                        other_result = group.get_result(result.name)
                        if (not first_is_reference
                        and other_result is not None
                        and other_result.avg < reference.avg):
                            reference = other_result
                    else:
                        other_result = None
                    if other_result is not None:
                        if totals[index+1] is not None:
                            totals[index+1] += other_result.avg
                    else:
                        totals[index+1] = None

                    results.append(other_result)
                table.add_results(result.name, results, first_is_reference)

            total_results = self.result_lists(totals)
            if 1 < len(first_group.results):
                table.add_results("Total", total_results, first_is_reference)
                table.has_total = True
            if totals_table is not None:
                for index, total in enumerate(totals):
                    if total is not None:
                        if all_totals[index] is not None:
                            all_totals[index] += total
                    else:
                        all_totals[index] = None
                totals_table.add_results(first_group.name, total_results, first_is_reference)

            table.display_table()

        if totals_table is not None:
            results = self.result_lists(all_totals)
            totals_table.add_results("Total", results, first_is_reference)
            totals_table.has_total = True
            totals_table.display_table()


class Application:
    def __init__(self, argv=None):
        self.parse_options(argv)
        self.config = BenchmarkConfig(self)
        self.platform_info = None
        self.campaigns = []
        self.current_campaign = None
        self.skip_benchmark = False

    def parse_options(self, cmdline_args):
        parser = OptionParser(usage="%prog [options] timeit STMT|timeit SETUP STMT|script filename.py|show FILE|compare FILE1 FILE2 ...|doctest")
        parser.add_option("--keyword", "-k",
            help="Filter group by their name using the specified KEYWORD",
            type="str", default=None, action="store")
        parser.add_option("--verbose", "-v",
            help="Verbose mode",
            default=False, action="store_true")
        parser.add_option("--debug",
            help="Debug mode",
            default=False, action="store_true")
        parser.add_option("--min-time",
            help="Minimum time in second of one point used to compute the number of loops (default: 100 ms)",
            type="float", default=0.1, action="store")
        parser.add_option("--max-time",
            help="Maximum time in second of one benchmark (default: 1 second)",
            type="float", default=1.0, action="store")
        parser.add_option("--min-repeat",
            help="Minimum number of repetition (default: 5)",
            type="int", default=5, action="store")
        parser.add_option("--file",
            help="Save output in the specified filename",
            type="str", default=None, action="store")

        options, args = parser.parse_args(cmdline_args)
        if not args:
            parser.print_help()
            sys.exit(1)
        self.options = options
        self.arguments = args[1:]
        self.command = args[0]
        self.timeit_stmt = None
        self.timeit_setup = None
        self.script = None
        if options.file and os.path.exists(options.file):
            print("ERROR: File %s already exists" % options.file)
            sys.exit(1)
        if self.command == "timeit":
            if not(2 <= len(args) <= 3):
                parser.print_help()
                sys.exit(1)
            if 2 < len(args):
                self.timeit_setup = args[1]
                self.timeit_stmt = args[2]
            else:
                self.timeit_stmt = args[1]
        if self.command == "script":
            if len(args) != 2 or not args[1]:
                parser.print_help()
                sys.exit(1)
            self.script = args[1]

    def get_current_campaign(self):
        if self.current_campaign is None:
            self.current_campaign = Campaign(self, name='')
            self.campaigns.append(self.current_campaign)
        return self.current_campaign

    def start_group(self, name):
        campaign = self.get_current_campaign()
        campaign.start_group(name)
        print("")
        print("[ %s ]" % name)
        print("")

    def timeit(self, stmt=None, setup=None, name=None, globals=None):
        if self.skip_benchmark:
            return
        campaign = self.get_current_campaign()
        try:
            runner = TimeitRunner(self, campaign, name, stmt, setup, globals)
            runner.run_benchmark()
        except Exception:
            err = sys.exc_info()[1]
            print(str(err))
            if setup is not None:
                print("setup: %s" % (setup,))
            print("stmt: %s" % (stmt,))

            raise
            sys.exit(1)

    def _bench_func(self, campaign, name, func):
        #runner = TimeitRunner(self, campaign, name, func, None)
        runner = FunctionRunner(self, campaign, name, func)
        runner.run_benchmark()

    def bench_func(self, name, func, *args, **kw):
        campaign = self.get_current_campaign()
        if args or kw:
            call_func = functools.partial(func, *args, **kw)
        else:
            call_func = func
        self._bench_func(campaign, name, call_func)

    def compare_functions(self, *functions):
        if len(functions) < 2:
            raise ValueError("Need a least 2 functions")
        campaign = self.get_current_campaign()
        for args in functions:
            name = args[0]
            func = args[1]
            func_args = args[2:]
            call_func = functools.partial(func, *func_args)
            self._bench_func(campaign, name, call_func)
        print("")
        campaign.current_group.compare_results()

    def load_campaign(self, filename):
        with open(filename, 'rb') as input_file:
            data = pickle.load(input_file)
        if data['format_version'] != 0:
            raise ValueError("Unknown format version (%s)" % data['format_version'])
        return Campaign(self, data=data['campaign'])

    def load_file(self, filename):
        campaign = self.load_campaign(filename)
        # FIXME: handle duplicate campaign names
        self.campaigns.append(campaign)
        if self.current_campaign is None:
            self.current_campaign = self.campaigns[0]

    def export(self):
        if not self.campaigns:
            raise ValueError("no campaign to save")
        if len(self.campaigns) != 1:
            raise ValueError("cannot save more than 1 campaign (got %s)"
                             % len(self.campaigns))
        campaign = self.campaigns[0]
        data = campaign.export()
        return {'format_version': 0, 'campaign': data}

    def save_file(self):
        filename = self.options.file
        if not filename:
            return
        data = self.export()
        with open(filename, 'wb') as output:
            pickle.dump(data, output)
        print("Results saved into %s" % filename)
        print("")

    def display_results(self, save=True):
        self.current_campaign.display_results()
        if save:
            self.save_file()
        dt = time.time() - self.start_time
        if dt > 2.0:
            print("Benchmark took %.1f sec" % dt)

    def run_timeit(self):
        self.platform_info = PlatformInfo()
        self.platform_info.collect_data(self.config)
        self.platform_info.display_all(self.options)

        self.timeit(stmt=self.timeit_stmt, setup=self.timeit_setup)
        print("")
        self.display_results()

    def _run_script(self, script, script_name):
        self.platform_info = PlatformInfo()
        self.platform_info.collect_data(self.config)
        self.platform_info.display_all(self.options)

        if not self.options.verbose:
            print("Run %s..." % script_name)
        script.run_benchmark(self)
        print("")
        if not self.current_campaign:
            print("ERROR: the script didn't run any benchmark")
            sys.exit(1)
        self.display_results()

    def run_script(self):
        import imp
        script = imp.load_source("script", self.script)
        name = "script %s" % self.script
        if self.options.keyword:
            self.skip_benchmark = True
        self._run_script(script, name)

    def load_results(self, filename):
        self.load_file(filename)
        self.platform_info = PlatformInfo()
        self.platform_info.collect_data(self.config)
        self.platform_info.display_all(self.options)
        self.display_results(save=False)

    def compare_files(self, first_is_reference):
        if len(self.arguments) < 2:
            print("Not at least two filenames to compare")
            sys.exit(1)
        files = []
        for filename in self.arguments:
            name = filename
            campaign = self.load_campaign(filename)
            if not campaign.name:
                campaign.name = name
            files.append(campaign)
        table = CampaignsTable(self, files)
        try:
            table.display(first_is_reference)
        except BrokenPipeError:
            pass

    def self_tests(self):
        import doctest
        nfailures, ntests = doctest.testmod()
        if nfailures:
            sys.exit(1)
        else:
            print("Doctests ok (%s tests)" % ntests)

    def main(self):
        self.start_time = time.time()
        if self.command == "script":
            self.run_script()
        elif self.command == "timeit":
            self.run_timeit()
        elif self.command == "show":
            if len(self.arguments) != 1:
                print("show requires a filename")
                sys.exit(1)
            self.load_results(self.arguments[0])
        elif self.command == "compare":
            self.compare_files(False)
        elif self.command == "compare_to":
            self.compare_files(True)
        elif self.command == "doctest":
            self.self_tests()
        else:
            raise ValueError("Unknown command: %r" % self.command)

def main():
    script = sys.modules['__main__']
    argv = ['script', script.__file__]
    name = os.path.basename(script.__file__)

    # FIXME: don't use private method here just to avoid imp.load_source()
    # and don't set start_time attribute
    app = Application(argv)
    app.start_time = time.time()
    app._run_script(script, name)

if __name__ == "__main__":
    Application().main()

