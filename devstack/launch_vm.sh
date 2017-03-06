#!/usr/bin/env bash

nova flavor-list
echo "Flavor ID:"
echo -n "> "
read flavor_id

nova image-list
echo "Image ID:"
echo -n "> "
read image_id

cmd="nova boot --flavor $flavor_id --image $image_id"

nova network-list
echo "Network ID (optional):"
echo -n "> "
read network_id

if [[ -n $network_id ]]; then
  cmd="$cmd --nic net-id=$network_id"
fi

nova keypair-list
echo "Keypair name (optional):"
echo -n "> "
read keypair_name

if [[ -n $keypair_name ]]; then
  cmd="$cmd --key-name $keypair_name $vm_name"
fi

ls -l *.cloudinit
echo "User data (optional):"
echo -n "> "
read user_data

if [[ -n $user_data ]]; then
    cmd="$cmd --user-data $user_data"
fi

echo "VM name:"
echo -n "> "
read vm_name

cmd="$cmd $vm_name"


echo $cmd > .launch_vm_lastcommand
echo $cmd
$cmd
