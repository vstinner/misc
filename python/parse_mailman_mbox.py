#!/usr/bin/env python3
import collections
import datetime
import email.utils
import mailbox
import statistics
import sys

days = collections.Counter()

filename = sys.argv[1]
box = mailbox.mbox(filename)
start_date = None
for msg in box.values():
    dates = msg.get_all('Date')
    if not dates or not dates[0]:
        print("BUG? invalid date:", dates)
        continue
    date = dates[0]

    date = email.utils.parsedate_tz(dates[0])
    dt = datetime.datetime(*date[:6]) - datetime.timedelta(seconds=date[-1])
    if start_date is None:
        start_date = dt.date()
    day = dt.day
    days[day] += 1

if 0:
    for day in range(1, 32):
        try:
            dt = start_date.replace(day=day)
        except ValueError:
            continue
        nmsg = days[day]
        print("%s: %s messages" % (dt, nmsg))
    print()

avg = statistics.mean(days.values())
nmsg, day = max((nmsg, day) for day, nmsg in days.items())
dt = start_date.replace(day=day)
total = sum(days.values())
print("Total: %s msg; avg: %.1f msg/day; max: %s msg at %s" % (total, avg, nmsg, dt))
