#!/usr/bin/env python3
import collections
import datetime
import email.utils
import mailbox
import statistics
import sys
import re

REGEX = re.compile(r'PEP ([0-9]{3,4})')

peps = collections.Counter()

for filename in sys.argv[1:]:
    box = mailbox.mbox(filename)
    for msg in box.values():
        subjects = msg.get_all('Subject')
        if not subjects or not subjects[0]:
            continue
        subject = subjects[0]

        match = REGEX.search(subject)
        if match is None:
            continue
        pep = int(match.group(1))
        peps[pep] += 1

items = sorted(((nmsg, pep) for pep, nmsg in peps.items()), reverse=True)
total = 0
for nmsg, pep in items:
    total += nmsg
    print("PEP %s: %s msg" % (pep, nmsg))

avg = total / len(items)
print("Total: %s msg; avg: %.1f msg/PEP" % (total, avg))
