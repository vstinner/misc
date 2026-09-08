set -x -e
for branch in main 3.15 3.14 3.13 3.12 3.11 3.10; do
    cd ~/python/$branch
    git checkout $branch
    git merge --ff
done
