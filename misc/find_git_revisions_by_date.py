#!/usr/bin/env python3
import datetime
import shlex
import subprocess
import sys


def get_output(*cmd):
    #print("+ " + ' '.join(map(shlex.quote, cmd)))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    if proc.returncode:
        sys.exit(proc.returncode)
    return proc.stdout.rstrip()


def _find_revision(git_dir, date, delta):
    start_date = date.strftime('%Y-%m-%d %H:%M:%SZ')
    end_date = (date + delta).strftime('%Y-%m-%d %H:%M:%SZ')

    stdout = get_output('git', '--git-dir', git_dir,
                        'log', '--after=%s' % start_date, '--before=%s' % end_date, '--reverse',
                        '--pretty=format:%H|%ci')
    if not stdout:
        return None

    line = stdout.splitlines()[0]

    revision, date = line.split('|')
    # drop second and timezone
    date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S %z')
    date = (date - date.utcoffset()).replace(tzinfo=datetime.timezone.utc)
    return (revision, date)

def find_revision(git_dir, date):
    days = 1
    while True:
        delta = datetime.timedelta(days=days)
        res = _find_revision(git_dir, date, delta)
        if res is not None:
            break

        days += 1
        if days > 7:
            print("Unable to the find the first commit of %s" % date)
            sys.exit(1)
    return res


def add_months(date, months):
    year = date.year
    month = date.month + months
    while month > 12:
        year += 1
        month -= 12
    return date.replace(year=year, month=month)


def main():
    git_dir = '/home/haypo/prog/python/master/.git'
    # quarters: 4 points per year
    points = 4
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
        revision, commit_date = find_revision(git_dir, date)
        print("%s - %s" % (revision, commit_date))

        date = add_months(date, months)
        if date >= end:
            break


if __name__ == "__main__":
    main()
