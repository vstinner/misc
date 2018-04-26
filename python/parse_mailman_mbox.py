#!/usr/bin/env python3
import mailbox
import datetime
import email.utils
import collections
import sys

days = collections.Counter()

filename = sys.argv[1]
box = mailbox.mbox(filename)
for msg in box.values():
    dates = msg.get_all('Date')
    if not dates or not dates[0]:
        print("BUG? invalid date:", dates)
        continue
    date = dates[0]

    date = email.utils.parsedate_tz(dates[0])
    dt = datetime.datetime(*date[:6]) + datetime.timedelta(seconds=date[-1])
    day = dt.day
    days[day] += 1

dt_month = dt
for day in range(1, 31):
    nmsg = days[day]
    dt = dt_month.date().replace(day=day)
    print("%s: %s" % (dt, nmsg))
print()

nmsg, day = max((nmsg, day) for day, nmsg in days.items())
dt = dt_month.date().replace(day=day)
print("Maximum: %s: %s" % (dt, nmsg))

total = sum(days.values())
print("Total: %s" % total)
