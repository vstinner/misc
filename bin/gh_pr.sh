set -e -x
if [[ "$1" = "-f" ]]; then
    force=-f
else
    force=
fi
local_branch=$(git name-rev --name-only HEAD)

project="$(basename $PWD)"
ref_branch=master

case "$project" in
    [23].[0-9])
        ref_branch=$project
        project=cpython
        ;;
    master)
        ref_branch=$project
        project=cpython
        ;;
esac

echo "branches: $local_branch -> $ref_branch"

git push haypo HEAD $force
URL="https://github.com/python/$project/compare/$ref_branch...haypo:$local_branch?expand=1"
python3 -m webbrowser $URL
