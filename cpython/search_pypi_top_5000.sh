if [ -z "$1" ]; then
    echo "usage: $0 pattern"
    exit 1
fi
rg -zl "$1" pypi-top-5000_2021-08-17/*.{zip,gz,bz2,tgz}
