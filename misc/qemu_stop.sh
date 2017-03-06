#!/bin/sh
set -b

ETH=eth0
TAP=tap0
BR=br0
TUN_FILE=/dev/net/tun

if [ $(sudo ifconfig -a|grep -c "^$TAP") -ne 0 ]; then
    echo "[+] Disable $TAP interface"
    sudo ifconfig $TAP down
    sudo tunctl -d $TAP
fi

if [ $(sudo ifconfig -a|grep -c "^$BR") -ne 0 ]; then
    echo "[+] Disable $BR interface"
    sudo ifconfig $BR down
    sudo brctl delbr $BR
fi

echo "[+] Disable $ETH and then restart network"
sudo ifconfig $ETH -promisc
sudo ifconfig $ETH down
sudo /etc/init.d/networking restart

