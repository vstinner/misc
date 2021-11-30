set -e -x
if [[ "$1" = "-f" ]]; then
    force=-f
else
    force=
fi
local_branch=$(git name-rev --name-only HEAD)

organization=python
project="$(basename $PWD)"
ref_branch=main

case "$project" in
    [23].[0-9])
        ref_branch=$project
        project=cpython
        ;;
    3.1[0-9])
        ref_branch=$project
        project=cpython
        ;;
    main)
        ref_branch=$project
        project=cpython
        ;;
    pyperf)
        project=pyperf
        organization=psf
        ;;
    peps)
        ref_branch=master
        ;;
esac

echo "branches: $local_branch -> $ref_branch"

git push origin HEAD $force
URL="https://github.com/$organization/$project/compare/$ref_branch...vstinner:$local_branch?expand=1"
python3 -m webbrowser $URL
