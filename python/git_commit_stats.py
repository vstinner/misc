import collections
import subprocess
proc = subprocess.run(['git', 'log', '--after=2018-05-01', 'master'],
                      stdout=subprocess.PIPE,
                      universal_newlines=True)
authors = collections.Counter()
for line in proc.stdout.splitlines():
    if line.startswith('Author: '):
        line = line[8:]
        name = line.split(' <')[0]
        authors[name] += 1
for name, commits in authors.most_common():
    if commits < 5:
        break
    print(commits, name)
