#!/usr/bin/env python3
import datetime
import re
import shlex
import subprocess
import sys


# '2.7', '3.3' but not 'master'
VERSION_REGEX = re.compile('^[0-9]\.[0-9]+$')


def add_months(date, months):
    year = date.year
    month = date.month + months
    while month > 12:
        year += 1
        month -= 12
    return date.replace(year=year, month=month)


class Application:
    def __init__(self):
        self.debug = False
        self.git_dir = '/home/haypo/prog/python/master/.git'
        self.remote = 'origin'

    def get_output(self, *cmd):
        if self.debug:
            print("+ " + ' '.join(map(shlex.quote, cmd)))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        if proc.returncode:
            sys.exit(proc.returncode)
        return proc.stdout.rstrip()

    def _find_revision(self, start_date, end_date):
        branch = 'remotes/%s/master' % self.remote
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%SZ')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%SZ')

        stdout = self.get_output('git', '--git-dir', self.git_dir,
                                 'log',
                                 '--after=%s' % start_date,
                                 '--before=%s' % end_date,
                                 '--first-parent',
                                 '--reverse',
                                 '--pretty=format:%H|%ci',
                                 branch)
        if not stdout:
            return None

        line = stdout.splitlines()[0]
        revision, date = line.split('|')

        # drop second and timezone
        date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S %z')
        date = (date - date.utcoffset()).replace(tzinfo=datetime.timezone.utc)
        return (revision, date)

    def find_revision(self, date):
        start_date = date
        one_day = datetime.timedelta(days=1)
        while True:
            res = self._find_revision(date, date + one_day)
            if res is not None:
                break

            date += one_day
            if (date - start_date).days > 15:
                print("Unable to find the first commit on %s..%s"
                      % (start_date, date))
                sys.exit(1)
        return res

    def main(self):
        # every month: 12 points per year
        points = 12
        # start date
        start = datetime.datetime(2014, 1, 1)
        year = 12
        if year % points:
            print("ERROR: cannot divide %s by %s" % (year, points))
            sys.exit(1)
        months = year // points

        date = start
        end = datetime.datetime.now()
        while True:
            revision, commit_date = self.find_revision(date)
            print("%s - %s" % (revision, commit_date))

            date = add_months(date, months)
            if date >= end:
                break


if __name__ == "__main__":
    Application().main()
