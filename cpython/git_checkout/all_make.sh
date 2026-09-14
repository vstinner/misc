set -e -x
for version in main 3.15 3.14 3.13; do
    (cd $version && make) || exit $?
done
# for version in 3.7 3.6 2.7; do
#     (cd $version && cp -f Modules/Setup.dist Modules/Setup && make) || exit $?
# done
