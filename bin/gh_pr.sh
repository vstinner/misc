set -e -x
if [[ "$1" = "-f" ]]; then
    force=-f
else
    force=
fi
local_branch=$(git name-rev --name-only HEAD)

if [ "$(basename $PWD)" = "buildmaster-config" ]; then
    project=buildmaster-config
    ref_branch=master
else
    project=cpython
    ref_branch=$(basename $(pwd))
fi
echo "branches: $local_branch -> $ref_branch"

git push haypo HEAD $force
URL="https://github.com/python/$project/compare/$ref_branch...haypo:$local_branch?expand=1"
python3 -m webbrowser $URL
