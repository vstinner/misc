#!/bin/bash
# set -e

# apt-get install bridge-utils
#    /usr/sbin/brctl
# apt-get install uml-utilities
#    /usr/sbin/tunctl

DHCP=0
IP=192.168.0.13
MASK=255.255.255.0
GW=192.168.0.254

ETH=eth0
TAP=tap0
BR=br0
TUN_FILE=/dev/net/tun

if [ "$USER" = "root" ]; then
    echo "Error: Don't run this script as root!"
    exit 1
fi

echo "[+] Check $TAP interface"

if [ $(sudo ifconfig -a|grep -c "^$TAP") -eq 0 ]; then
    echo "[+] Create $TAP interface"
    sudo tunctl -t $TAP -u $USER
fi

echo "[+] Disable DHCP client, bridge $BR, interfaces $ETH and $TAP"
sudo killall dhclient dhclient3 2>/dev/null || true
if [ $? -eq 0 ]; then
    sleep 1
    sudo killall -9 dhclient dhclient3 2>/dev/null
fi
sudo ifconfig $BR down 2>/dev/null
sudo brctl delbr $BR 2>/dev/null
sudo ifconfig $ETH down
sudo ifconfig $TAP down

echo "[+] Recreate and setup bridge $BR"
sudo brctl addbr $BR
sudo ifconfig up
sudo brctl stp $BR off
sudo brctl setfd $BR 1
sudo brctl sethello $BR 1
sudo brctl addif $BR $ETH
sudo brctl addif $BR $TAP

echo "[+] Enable promiscious mode of interfaces $ETH and $TAP"
sudo ifconfig $ETH 0.0.0.0 promisc up
sudo ifconfig $TAP 0.0.0.0 promisc up

if [ $DHCP -eq 1 ]; then
    echo "[+] Run dhclient $BR"
    sudo dhclient $BR
else
    echo "[+] Set $BR address ($IP/$MASK)"
    sudo ifconfig $BR $IP netmask $MASK up # broadcast 192.168.33.255 up

    echo "[+] Set default gateway ($GW)"
    sudo route add default gw $GW
fi

echo "[+] Check $TUN_FILE file permissions"
if [ ! -r $TUN_FILE ]; then
    echo "[+] Fix $TUN_FILE permissions (666)"
    sudo chmod 666 $TUN_FILE
fi

# echo "[+] Check kqemu kernel module"
# if [ ! -e /dev/kqemu ]; then
#     echo "[+] Load kqemu kernel module"
#     sudo modprobe kqemu
# fi

echo
echo "Network setup done: public IP is $IP/$MASK"

