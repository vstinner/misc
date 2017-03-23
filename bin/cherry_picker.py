#!/usr/bin/env python3
# wget https://github.com/python/core-workflow/raw/master/cherry_picker/cherry_picker.py
import click
import os
import subprocess
import webbrowser


@click.command()
@click.option('--dry-run', is_flag=True)
@click.option('--push', 'pr_remote', metavar='REMOTE',
              help='git remote to use for PR branches', default='origin')
@click.argument('commit_sha1', 'The commit sha1 to be cherry-picked')
@click.argument('branches', 'The branches to backport to', nargs=-1)
def cherry_pick(dry_run, pr_remote, commit_sha1, branches):
    if not os.path.exists('./pyconfig.h.in'):
        os.chdir('./cpython/')
    upstream = get_git_fetch_remote()
    username = get_forked_repo_name(pr_remote)

    if dry_run:
       click.echo("Dry run requested, listing expected command sequence")


    click.echo("fetching upstream ...")
    run_cmd("git fetch {upstream}".format_map(locals()), dry_run=dry_run)

    if not branches:
        raise ValueError("at least one branch is required")

    for branch in branches:
        click.echo("Now backporting '{commit_sha1}' into '{branch}'".format_map(locals()))

        # git checkout -b 61e2bc7-3.5 upstream/3.5
        cherry_pick_branch = "backport-{commit_sha1[:7]}-{branch}".format_map(locals())
        cmd = "git checkout -b {cherry_pick_branch} {upstream}/{branch}".format_map(locals())
        run_cmd(cmd, dry_run=dry_run)

        cmd = "git cherry-pick -x {commit_sha1}".format_map(locals())
        if run_cmd(cmd, dry_run=dry_run):
            cmd = "git push {pr_remote} {cherry_pick_branch}".format_map(locals())
            if not run_cmd(cmd, dry_run=dry_run):
                click.echo("Failed to push to {pr_remote} :(".format_map(locals()))
            else:
                open_pr(username, branch, cherry_pick_branch, dry_run=dry_run)
        else:
            click.echo("Failed to cherry-pick {commit_sha1} into {branch} :(".format_map(locals()))

        cmd = "git checkout master"
        run_cmd(cmd, dry_run=dry_run)

        cmd = "git branch -D {cherry_pick_branch}".format_map(locals())
        if run_cmd(cmd, dry_run=dry_run):
            if not dry_run:
                click.echo("branch {cherry_pick_branch} has been deleted.".format_map(locals()))
        else:
            click.echo("branch {cherry_pick_branch} NOT deleted.".format_map(locals()))


def get_git_fetch_remote():
    """Get the remote name to use for upstream branches
    Uses "upstream" if it exists, "origin" otherwise
    """
    cmd = "git remote get-url upstream"
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return "origin"
    return "upstream"


def get_forked_repo_name(pr_remote):
    """
    Return 'myusername' out of https://github.com/myusername/cpython
    :return:
    """
    cmd = "git config --get remote.{pr_remote}.url".format_map(locals())
    raw_result = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    result = raw_result.decode('utf-8')
    username_end = result.index('/cpython.git')
    if result.startswith("https"):
        username = result[len("https://github.com/"):username_end]
    else:
        username = result[len("git@github.com:"):username_end]
    return username


def run_cmd(cmd, *, dry_run=False):
    if dry_run:
        click.echo("  dry-run: {cmd}".format_map(locals()))
        return True
    try:
        subprocess.check_output(cmd.split())
    except subprocess.CalledProcessError:
        return False
    return True


def open_pr(forked_repo, base_branch, cherry_pick_branch, *, dry_run=False):
    """
    construct the url for pull request and open it in the web browser
    """
    url = "https://github.com/python/cpython/compare/{base_branch}...{forked_repo}:{cherry_pick_branch}?expand=1".format_map(locals())
    if dry_run:
        click.echo("  dry-run: Create new PR: {url}".format_map(locals()))
        return
    webbrowser.open_new_tab(url)


if __name__ == '__main__':
    cherry_pick()
