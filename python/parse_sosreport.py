#!/usr/bin/env python3
"""
Parse sosreport reports: 1 or multiple files, try to rebuild a kind of
"timeline".

General options:

  -w, --warnings        Set log level to WARNING
  -e, --errors          Set log level to ERROR
  -q, --quiet           Quiet mode: don't log progress
  -H, --with-filename   Display logs with the source filename
  -d DIRECTORY, --directory DIRECTORY
                        Root directory of sosreport reports
                        (default: current working directory)
  -u, --unsorted        Don't rebuild the timeline (don't sort by date)

Commands:

services
    List running OpenStack services according to the 'ps' file.
ip_addr
    Get IP addresses from 'ip_addr' files.
    Ignore host and link scopes (ex: ignore 127.0.0.1 and fe80:xxx).
errors
    Search for the most critical errors.
warnings
    Parse all logs and display warnings and errors.
all
    Parse all logs.
rabbitmq
    Parse RabbitMQ logs.
oslo_messaging
    Search for Oslo Messaging warnings and errors in OpenStack services logs.
database
    Search for DBConnectionError in OpenStack services logs.
yum
    Read yum.log logs.
grep PATTERN
    Search PATTERN in all

See also https://github.com/mangelajo/os-log-merger
"""
from __future__ import print_function
import argparse
import collections
import datetime
import errno
import functools
import io
import ipaddress
import logging
import os.path
import re
import shlex
import sys
import traceback

OSLO_MESSAGING_REGEXES = (
    (r'Failed to consume message from queue: ', logging.ERROR),
    (r'MessagingTimeout: Timed out waiting for a reply to message ID ', logging.WARNING),

    (r'Reconnected to AMQP server on', logging.INFO),

    (r'AMQP server on .* is unreachable:', logging.DEBUG),
)

DATABASE_REGEXES = (
    # match DBConnectionError, but not 'DBConnectionError
    # nor "DBConnectionError to ignore tracebacks logged on the client side
    (r'''(?<!['"])DBConnectionError''', logging.WARNING),
)

RABBITMQ_PATTERNS = (
    ('^Mnesia', logging.ERROR),
    ('^Cluster ', logging.ERROR),

    ('^Stopped ', logging.WARNING),
    ('^Starting ', logging.WARNING),

    ('^Stopping ', logging.INFO),
)

MYSQL_REGEX = (
    (r'turning message relay requesting on', logging.ERROR),
    (r'Starting mysqld daemon', logging.WARNING),
    (r'mysqld from pid file .* ended', logging.WARNING),
)

PROCESS_WHITELIST = (
    # aodh-evaluator, aodh-listener, aodh-notifier, aodh_wsgi
    'aodh',
    # RabbitMQ
    # ceilometer-agent-notification, ceilometer-collector, ceilometer-polling,
    # ceilometer_wsgi
    'ceilometer',
    # ceph-mon, ceph-osd
    'ceph',
    # cinder-scheduler, cinder-volume, cinder_wsgi
    'cinder',
    # docker-containerd-current, dockerd-current
    'docker',
    # glance-api, glance-registry
    'glance',
    # gnocchi-metricd:, gnocchi-statsd, gnocchi_wsgi
    'gnocchi',
    # haproxy-systemd-wrapper, haproxy
    'haproxy',
    # heat-api-cfn, heat-api-cloudwatch, heat-api, heat-engine
    'heat',
    # httpd
    'httpd',
    # ironic-api, ironic-conductor, ironic-inspector
    'ironic',
    # keepalived
    'keepalived',
    # keystone-admin, keystone-main
    'keystone',
    # libvirtd
    'libvirtd',
    # memcached
    'memcached',
    # mistral-server
    'mistral',
    # mongod
    'mongod',
    # mysqld
    'mysqld',
    # neutron-dhcp-agent
    # neutron-keepalived-state-change
    # neutron-l3-agent
    # neutron-metadata-agent
    # neutron-ns-metadata-proxy
    # neutron-openvswitch-agent
    # neutron-rootwrap-daemon
    # neutron-rootwrap
    # neutron-server
    'neutron',
    # nova-api
    # nova-cert
    # nova-compute
    # nova-conductor
    # nova-consoleauth
    # nova-novncproxy
    # nova-scheduler
    'nova',
    # ovsdb-client
    # ovsdb-server
    'ovsdb',
    # ovs-vswitchd
    'ovs',
    # pacemakerd
    'pacemakerd',
    # qemu-kvm
    'qemu-kvm',
    # redis-server
    'redis',
    # /usr/lib/rabbitmq/bin/rabbitmq-server
    'rabbitmq-server',
    # mysqld_safe
    'mysql',
    # swift-account-auditor
    # swift-account-reaper
    # swift-account-replicator
    # swift-account-server
    # swift-container-auditor
    # swift-container-replicator
    # swift-container-server
    # swift-container-updater
    # swift-object-auditor
    # swift-object-expirer
    # swift-object-replicator
    # swift-object-server
    # swift-object-updater
    # swift-proxy-server
    'swift',
    # zaqar-server
    'zaqar',
)


def build_regexes(regexes):
    regex_all = '(?:%s)' % '|'.join(regex for regex, level in regexes)
    flags = re.MULTILINE
    regex_all = re.compile(regex_all, flags)
    regexes = [(re.compile(regex, flags), level) for regex, level in regexes]
    return (regex_all, regexes)


def get_regex_level(regexes, text):
    for regex, level in regexes:
        if regex.search(text):
            break
    return level


def join_path(path, name):
    if path != os.path.curdir:
        return os.path.join(path, name)
    else:
        return name


def _find_file(path, filename, result, max_depth):
    if max_depth is not None and max_depth != 1:
        raise ValueError("only max_depth=None or max_depth=1 are supported")

    for rootdir, dirnames, filenames in os.walk(path):
        for name in filenames:
            if name == filename:
                fullname = join_path(rootdir, name)
                result.append(fullname)

        if max_depth is not None:
            depth = max_depth
            testdir = rootdir
            while testdir != path:
                depth -= 1
                if depth < 0:
                    # don't go deeper
                    del dirnames[:]
                    break
                testdir = os.path.dirname(testdir)

def _find_directory(path, directory, result):
    for rootdir, dirnames, filenames in os.walk(path):
        for dirname in dirnames:
            fullname = join_path(rootdir, dirname)
            if fullname.endswith(directory):
                result.append(fullname)


class Log(object):
    def __init__(self, msg, filename=None, lineno=None, host=None, level=None):
        self.msg = msg
        self.filename = filename
        self.lineno = lineno
        self.host = host
        if level is not None:
            self.level = level
        else:
            self.level = logging.WARNING

    def _format_prefix(self, filename, lineno_delta=0):
        parts = []
        if self.host:
            parts.append(self.host)
        if filename and self.filename:
            parts.append(self.filename)
            if self.lineno:
                parts.append(str(self.lineno + lineno_delta))
        return ':'.join(parts)

    def format(self, filename=False):
        prefix = self._format_prefix(filename)
        return '%s: %s' % (prefix, self.msg)

    def format_lines(self, filename=False):
        lines = []
        for lineno_delta, line in enumerate(self.msg.splitlines()):
            prefix = self._format_prefix(filename, lineno_delta)
            lines.append("%s: %s" % (prefix, line))
        return lines

    def __str__(self):
        return self.format()


class TimelineLog(Log):
    def __init__(self, date, msg, filename=None, lineno=None, host=None,
                 level=None):
        super(TimelineLog, self).__init__(msg, filename, lineno, host, level)
        self.date = date

    @staticmethod
    def sort_key(log):
        return log.date


class FileParser(object):
    def __init__(self, app):
        self.app = app
        self.filename = None
        self.lineno = None
        self.logger = app.log

    def open(self, filename):
        self.filename = filename
        return io.open(filename, encoding="utf-8")

    def iter_lines(self, fp):
        for lineno, line in enumerate(fp, 1):
            self.lineno = lineno
            yield line

    def prepare_log(self, log):
        pass

    def _log(self, log):
        self.prepare_log(log)
        self.logger(log)

    def log(self, msg):
        if not self.filename:
            raise ValueError("filename is not set")
        log = Log(msg,
                  filename=self.filename,
                  lineno=self.lineno,
                  host=self.app.host)
        self._log(log)

    def timeline_log(self, date, msg, level=None):
        if not self.filename:
            raise ValueError("filename is not set")
        log = TimelineLog(date, msg,
                          filename=self.filename,
                          lineno=self.lineno,
                          host=self.app.host,
                          level=level)
        self._log(log)

    def parse_error(self, exc):
        msg = "Parser error at %s:%s" % (self.filename, self.lineno)
        self.app.fatal_exc(msg, exc)

    def _parse(self, parse_line, filename):
        try:
            with self.open(filename) as fp:
                for line in self.iter_lines(fp):
                    parse_line(line)
        except Exception as exc:
            self.parse_error(exc)

    def parse_date(self, line):
        raise ValueError("failed to parse date: %r" % line)

    def log_grep(self, line):
        if self.app.args.unsorted:
            self.log(line)
        else:
            try:
                dt = self.parse_date(line)
            except Exception as exc:
                raise Exception("parse_date() error, try --unsorted, error: %s"
                                % exc)
            self.timeline_log(dt, line)

    def _grep(self, regex, line):
        if not regex.search(line):
            return

        line = line.rstrip()
        self.log_grep(line)

    def grep(self, filename, regex):
        parse_line = functools.partial(self._grep, regex)
        self._parse(parse_line, filename)


class YumLogParser(FileParser):
    def _parse_line(self, line):
        # Apr 23 13:27:54
        dt = datetime.datetime.strptime(line[:15], "%b %d %H:%M:%S")
        dt = dt.replace(year=self.app.fixup_date.year)
        self.timeline_log(dt, line, level=logging.INFO)

    def parse(self, filename):
        self._parse(self._parse_line, filename)


class MySQLLogParser(FileParser):
    def __init__(self, app):
        super(MySQLLogParser, self).__init__(app)
        self.regex_all, self.regexes = build_regexes(MYSQL_REGEX)
        self.date_regex = re.compile('^[0-9]+ ([0-9]+):([0-9]+):([0-9]+) ')

    def parse_date(self, line):
        # 13:24:19
        match = self.date_regex.match(line)
        if not match:
            raise ValueError("failed to parse MySQL date: %r" % line)
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3))

        date = self.app.fixup_date
        return date.replace(hour=hour, minute=minute, second=second)

    def _parse_line(self, line):
        if not self.regex_all.search(line):
            return
        date = self.parse_date(line)
        level = get_regex_level(self.regexes, line)
        self.timeline_log(date, line.rstrip(), level=level)

    def parse(self, filename):
        self._parse(self._parse_line, filename)


class OpenStackLogParser(FileParser):
    def __init__(self, app):
        super(OpenStackLogParser, self).__init__(app)
        regex = r'(20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\.[0-9]{3}'
        self.cleanup_ts_us= re.compile(regex)
        regex = (r'[0-9]+ ERROR ([a-z0-9_]+(?:\.[a-z0-9_]+)* )'
                 r'(?:\[(?:-|req-[0-9a-f-]{36} - - - - -)\] )?')
        self.cleanup_prefix = re.compile(regex)
        regex = r'\[[0-9a-f-]{36}\] '
        self.cleanup_uuid_regex = re.compile(regex)
        self.raw = app.args.raw

    @staticmethod
    def _replace_ts(match):
        return match.group(1)

    @staticmethod
    def _replace_prefix(match):
        return match.group(1)

    def prepare_log(self, log):
        # 15165 ERROR oslo.messaging._drivers.impl_rabbit [-]
        if not self.raw:
            msg = log.msg
            msg = self.cleanup_ts_us.sub(self._replace_ts, msg)
            msg = self.cleanup_prefix.sub(self._replace_prefix, msg)
            msg = self.cleanup_uuid_regex.sub('', msg)
            log.msg = msg

    def _parse_date(self, line):
        try:
            # /var/log/nova-compute.log
            # 2017-04-23 13:19:58.096 93150 ERROR oslo.messaging._drivers ...
            dt = datetime.datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
            return (dt, True)
        except ValueError:
            pass

        try:
            # /var/log/anaconda/journal.log
            # Oct 10 23:09:06 localhost kernel: acpi ...
            dt = datetime.datetime.strptime(line[:15], "%b %d %H:%M:%S")
            dt = dt.replace(year=self.app.fixup_date.year)
            return (dt, False)
        except ValueError:
            pass

        raise ValueError("failed to parse date: %r" % line)

    def parse_date(self, line):
        dt, store = self._parse_date(line)
        if store:
            self.date = dt
        return dt


class RabbitMQParser(FileParser):
    def __init__(self, app):
        super(RabbitMQParser, self).__init__(app)
        self.header_regex = re.compile(r'=(?:INFO|WARNING|ERROR) REPORT==== (.*) ===')
        self.regex_all, self.regexes = build_regexes(RABBITMQ_PATTERNS)
        self.raw = app.args.raw

    def prepare_log(self, log):
        # 15165 ERROR oslo.messaging._drivers.impl_rabbit [-]
        if not self.raw:
            msg = log.msg
            if ": Starting" in msg:
                msg = msg.splitlines()[0]
            log.msg = msg

    def parse_header(self, line):
        match = self.header_regex.match(line)
        if not match:
            raise ValueError("failed to parse line %r" % line)
        line = match.group(1)

        # 23-Apr-2017::13:55:09
        try:
            dt = datetime.datetime.strptime(line, "%d-%b-%Y::%H:%M:%S")
        except ValueError:
            raise ValueError("failed to parse the date: %r" % line)
        self.date = dt
        return (dt, line)

    def parse_date(self, line):
        return dt

    def iter_lines(self, fp):
        self.header = None
        lines = []
        first_line = None
        for lineno, line in enumerate(fp, 1):
            self.lineno = lineno

            if self.header_regex.match(line):
                if lines and self.header:
                    self.lineno = first_line
                    yield ''.join(lines)

                self.header = line
                del lines[:]
            else:
                if not lines:
                    first_line = lineno
                lines.append(line)

        if lines:
            self.lineno = first_line
            yield ''.join(lines)

    def _parse_line(self, line):
        # quick tests
        if not self.regex_all.search(line):
            return

        level = get_regex_level(self.regexes, line)
        dt, text = self.parse_header(self.header.rstrip())
        text = '%s: %s' % (text, line.rstrip())
        self.timeline_log(dt, text, level=level)

    def parse(self, filename):
        self._parse(self._parse_line, filename)

    def log_grep(self, line):
        if self.app.args.unsorted:
            self.log(line)
        else:
            try:
                if not self.header:
                    raise ValueError("no header")
                dt, header = self.parse_header(self.header)
                line = "%s: %s" % (header, line)
            except Exception as exc:
                raise Exception("failed to parse RabbitMQ header date, "
                                "try --unsorted, error: %s" % exc)
            self.timeline_log(dt, line)


class SOSReportParser(object):
    def __init__(self):
        self.filename = '<unset>'
        self.host = '<unset>'
        self.min_log_level = logging.DEBUG
        # Date used to fix incomplete dates in parse_date(), should be
        # updated when a valid date is found
        self.fixup_date = datetime.datetime.now()
        # list of Log instances
        self._timeline = []

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-w', '--warnings', action='store_true',
                            help='Set log level to WARNING')
        parser.add_argument('-e', '--errors', action='store_true',
                            help='Set log level to ERROR')
        parser.add_argument('-q', '--quiet', action='store_true',
                            help="Quiet mode: don't log progress")
        parser.add_argument('--raw', action='store_true',
                            help="Don't cleanup logs")
        parser.add_argument('-H', '--with-filename', action='store_true',
                            help='Display logs with the source filename')
        parser.add_argument('-d', '--directory', default=os.path.curdir,
                            help='Root directory of sosreport reports '
                                 '(default: current working directory)')
        parser.add_argument('-u', '--unsorted', action='store_true',
                            help="Don't rebuild the timeline "
                                 "(don't sort by date)")

        subparsers = parser.add_subparsers(dest='action')
        for action in ('ip_addr', 'rabbitmq', 'services',
                       'all', 'warnings', 'errors',
                       'oslo_messaging', 'database', 'yum',
                       'mysql'):
            cmd = subparsers.add_parser(action)

        cmd = subparsers.add_parser('grep',
                                    help="Search PATTERN in var/log/**.log")
        cmd.add_argument('pattern')

        self.args = parser.parse_args()

        if not self.args.action:
            parser.print_help()
            sys.exit(1)

        if self.args.errors:
            self.min_log_level = logging.ERROR
        elif self.args.warnings:
            self.min_log_level = logging.WARNING

        self.directory = self.args.directory

    def set_context(self, filename):
        if not self.args.quiet:
            print("Parse file: %s" % filename, file=sys.stderr)
            sys.stderr.flush()
        self.filename = filename
        self.host = self.filename_to_host(filename)

    def _log(self, log):
        for line in log.format_lines(filename=self.args.with_filename):
            print(line)

    def log(self, log=None):
        if isinstance(log, str):
            log = Log(log, host=self.host, filename=self.filename)
        elif not isinstance(log, Log):
            raise TypeError("expect str or Log")

        if log.level < self.min_log_level:
            return

        if not isinstance(log, TimelineLog) or self.args.unsorted:
            self._log(log)
        else:
            self._timeline.append(log)

    def newline(self):
        print()

    def find_file(self, path, filename, max_depth=None):
        result = []
        _find_file(path, filename, result, max_depth)
        result.sort()
        return result

    def find_directory(self, directory):
        if directory.endswith(os.path.sep):
            directory = directory[:-1]
        result = []
        _find_directory(self.directory, directory, result)
        return result

    @staticmethod
    def cat(filename):
        self.get_hosts()

        with open(filename) as fp:
            for line in fp:
                line = line.rstrip()
                print(line)

    def filename_to_host(self, filename):
        filename = os.path.abspath(filename)
        parts = filename.split(os.path.sep)
        if parts[0] == os.path.curdir:
            del parts[0]

        for name in reversed(parts):
            match = re.match(r'^sosreport-(.*)-[0-9]+$', name)
            if match:
                name = match.group(1)
                break
        else:
            name = parts[-1]

        if name.endswith(".redhat.local"):
            name = name[:-len(".redhat.local")]
        return name

    def fatal_error(self, message):
        print("ERROR: %s" % message)
        sys.exit(1)

    def fatal_exc(self, message, exc):
        print("ERROR: %s: [%s] %s" % (message, type(exc).__name__, exc))
        traceback.print_exc()
        sys.exit(1)

    def get_ip_addr(self, filename):
        addresses = []
        with open(filename) as fp:
            for line in fp:
                # ignore host and link scopes
                if 'scope host' in line:
                    continue
                if 'scope link' in line:
                    continue
                match = re.search(r'inet6? ([0-9a-f:.]+/[0-9]+)', line)
                if not match:
                    self.fatal_error("failed to parse %r of %s" % (line, filename))
                addr = match.group(1)
                addr, network = addr.split('/', 1)
                addr = ipaddress.ip_address(addr)
                addresses.append((addr, int(network)))

        if addresses:
            def sort_func(item):
                addr, network = item
                return (addr.version, addr, network)

            addresses = sorted(addresses, key=sort_func)
            host = self.filename_to_host(filename)
            for addr, network in addresses:
                self.log("%s/%s" % (addr, network))
            self.newline()

    def action_ip_addr(self):
        for filename in self.find_file(self.directory, 'ip_addr', max_depth=1):
            self.set_context(filename)
            self.get_ip_addr(filename)

    def action_rabbitmq(self):
        for path in self.find_directory('var/log/rabbitmq/'):
            for name in os.listdir(path):
                if name.endswith("sasl.log"):
                    continue
                if name.endswith(".log"):
                    log_file = join_path(path, name)
                    break
            else:
                self.fatal_error("No LOG found in %s" % path)

            self.set_context(log_file)
            RabbitMQParser(self).parse(log_file)

    def dump_timeline(self):
        logs = sorted(self._timeline, key=TimelineLog.sort_key)
        if not logs:
            return

        first = logs[0].date
        last = logs[-1].date
        dt = last - first
        if not self.args.quiet:
            print(file=sys.stderr)
            sys.stderr.flush()

        print("Timeline: %s - %s (%s)" % (first, last, dt))
        print()

        date = None
        for log in logs:
            if date is not None:
                dt = log.date - date
                if dt > datetime.timedelta(minutes=1):
                    print()
                    print("Date +%s" % dt)

            self._log(log)
            date = log.date

    def get_parser(self, filename):
        if os.path.basename(os.path.dirname(filename)) == 'rabbitmq':
            return RabbitMQParser(self)
        else:
            return OpenStackLogParser(self)

    def grep_log_file(self, filename, regex, logger=None):
        parser = self.get_parser(filename)
        self.set_context(filename)
        if logger is not None:
            parser.logger = logger
        parser.grep(filename, regex)

    def grep_var_log(self, regex, logger=None):
        for path in self.find_directory('var/log/'):
            for rootdir, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if not filename.endswith(".log"):
                        continue
                    fullname = join_path(rootdir, filename)
                    self.grep_log_file(fullname, regex, logger)

    def action_grep(self):
        regex = re.compile(self.args.pattern)
        self.grep_var_log(regex)

    def action_oslo_messaging(self):
        regex_all, regexes = build_regexes(OSLO_MESSAGING_REGEXES)

        def logger(log):
            log.level = get_regex_level(regexes, log.msg)
            self.log(log)

        self.grep_var_log(regex_all, logger=logger)

    def action_database(self):
        regex_all, regexes = build_regexes(DATABASE_REGEXES)

        def logger(log):
            log.level = get_regex_level(regexes, log.msg)
            self.log(log)

        self.grep_var_log(regex_all, logger=logger)

    def action_yum(self):
        for filename in self.find_file(self.directory, 'yum.log'):
            self.set_context(filename)
            YumLogParser(self).parse(filename)

    def action_mysql(self):
        for filename in self.find_file(self.directory, 'mysqld.log'):
            self.set_context(filename)
            MySQLLogParser(self).parse(filename)

    def get_processes(self, filename):
        processes = []
        with io.open(filename, encoding="utf-8") as fp:
            # ignore header line
            fp.readline()
            for line in fp:
                fields = shlex.split(line)
                args = fields[10:]
                processes.append(args)
        return processes

    def list_processes(self, processes):
        names = collections.defaultdict(collections.Counter)
        for args in processes:
            i = 0
            while True:
                exe = args[i]
                if not(exe.startswith('[') and exe.endswith(']')):
                    exe = os.path.basename(exe)
                if exe in ('sudo', 'python', 'python2', 'bash', 'sh'):
                    i += 1
                    while args[i].startswith('-'):
                        i += 1
                elif exe == 'timeout' and args[i+1].endswith('s'):
                    i += 2
                else:
                    break
            for name in PROCESS_WHITELIST:
                if name in exe:
                    break
            else:
                continue
            names[name][exe] += 1


        names = sorted(names.items())
        for service, counter in names:
            total = sum(counter.values())
            if total > 1:
                service = '%s (%s)' % (service, total)

            items = counter.most_common()
            items = ', '.join('%s (%s)' % (name, count) if count > 1 else name
                              for name, count in sorted(items))

            self.log("%s: %s" % (service, items))
        self.newline()

    def action_services(self):
        for filename in self.find_file(self.directory, 'ps', max_depth=1):
            self.set_context(filename)
            processes = self.get_processes(filename)
            self.list_processes(processes)

    def parse_all(self):
        self.action_oslo_messaging()
        self.action_rabbitmq()
        self.action_database()
        self.action_yum()
        self.action_mysql()

    def action_warnings(self):
        self.min_log_level = logging.WARNING
        self.parse_all()

    def action_all(self):
        self.parse_all()

    def action_errors(self):
        self.min_log_level = logging.ERROR
        self.parse_all()

    def get_date(self):
        for filename in self.find_file(self.directory, 'date', max_depth=1):
            if os.path.basename(os.path.dirname(filename)) == 'bin':
                # skip bin/date
                continue
            self.set_context(filename)

            with io.open(filename, encoding="utf-8") as fp:
                line = fp.readline().rstrip()

            # Sun Apr 23 15:26:02 UTC 2017
            date = datetime.datetime.strptime(line,
                                              "%a %b %d %H:%M:%S UTC %Y")
            self.fixup_date = date
            break

        if not self.args.quiet:
            print("Set fixup date to %s" % self.fixup_date, file=sys.stderr)

    def _main(self):
        self.parse_args()
        print("Parse directory: %s" % os.path.abspath(self.directory),
              file=sys.stderr)

        self.get_date()

        action = self.args.action
        meth = getattr(self, 'action_' + action)
        try:
            meth()
        except Exception as exc:
            self.fatal_exc("Error in action %s on parsing file %s" % (action, self.filename), exc)
        self.dump_timeline()

    def main(self):
        try:
            self._main()
        except OSError as exc:
            # catch BrokenPipeError
            if exc.errno != erro.EPIPE:
                raise

            # Close stdout and stderr to prevent Python warning at exit
            try:
                sys.stdout.close()
            except OSError:
                pass
            try:
                sys.stderr.close()
            except OSError:
                pass


if __name__ == "__main__":
    SOSReportParser().main()
