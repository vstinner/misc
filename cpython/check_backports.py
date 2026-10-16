import shlex
import os
import subprocess
import sys
import re


MAIN_BRANCH = 'main'
BRANCHES = ("3.15", "3.14")
SRC_DIR = os.getcwd()
CHERRY_PICK = '(cherry picked from commit {})'
GIT_COMMAND = [
    'git',
    '--git-dir', os.path.join(SRC_DIR, '.git'),
    '--work-tree', SRC_DIR,
]
# Match '(#155492)' trailer
GITHUB_ISSUE_REGEX = re.compile(r'\(#([0-9]{6})\)$')


def get_output(cmd):
    print('+ ' + shlex.join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          text=True,
                          check=True)
    return proc.stdout


def get_commit_filename(branch):
    return f'COMMITS-{branch}'


def get_commits(branch, author, date):
    filename =  get_commit_filename(branch)
    if os.path.exists(filename):
        return

    cmd = [*GIT_COMMAND,
           'log',
           f'--after={date}']
    if author:
        cmd.append(f'--author={author}')
    cmd.append(branch)

    output = get_output(cmd)
    with open(filename, 'w') as fp:
        fp.write(output)


def replace_github_issue(regs):
    issue = regs.group(1)
    # Replace '(#155492)' with '(GH-155492)'
    return f'(GH-{issue})'


def check_commit(commit, summary, branches):
    patterns = [CHERRY_PICK.format(commit), summary]
    if GITHUB_ISSUE_REGEX.search(summary) is not None:
        summary2 = GITHUB_ISSUE_REGEX.sub(replace_github_issue, summary)
        patterns.append(summary2)

    for branch, lines in branches:
        for line_number, line in enumerate(lines):
            if not any(pattern in line for pattern in patterns):
                continue

            while True:
                line_number -= 1
                if line_number < 0:
                    print("ERROR: unable to get backport commit in branch {branch}")
                    sys.exit(1)

                if lines[line_number].startswith('commit '):
                    backport_commit = lines[line_number].removeprefix('commit ').strip()
                    break

            patterns.append(CHERRY_PICK.format(backport_commit))
            break
        else:
            print(f"TODO: {commit} not backported to {branch}: {summary}")


def main():
    if len(sys.argv) != 3:
        print(f"usage: python {sys.argv[0]} AUTHOR DATE")
        sys.exit(1)
    author = sys.argv[1]
    date = sys.argv[2]

    for branch in [MAIN_BRANCH, *BRANCHES]:
        if branch == MAIN_BRANCH:
            get_commits(branch, author, date)
        else:
            get_commits(branch, None, date)

    checked_branches = []
    for branch in BRANCHES:
        filename = get_commit_filename(branch)
        with open(filename) as fp:
            lines = fp.readlines()
        checked_branches.append((branch, lines))

    filename = get_commit_filename('main')
    with open(filename) as fp:
        lines = fp.readlines()

    for line_number in range(len(lines) - 1, -1, -1):
        line = lines[line_number]
        if not line.startswith('commit '):
            continue

        commit = line.removeprefix('commit ').strip()
        while True:
            line_number += 1
            if lines[line_number].startswith(' ' * 4):
                summary = lines[line_number][4:].strip()
                if summary:
                    break
        else:
            print("ERROR: unable to get commit summary")
            sys.exit(1)

        check_commit(commit, summary, checked_branches)


if __name__ == "__main__":
    main()
