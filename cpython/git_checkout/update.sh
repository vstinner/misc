set -x -e

cd ~/python/main
git fetch upstream --tags --prune
git fetch origin --prune

../reset_branches.sh
