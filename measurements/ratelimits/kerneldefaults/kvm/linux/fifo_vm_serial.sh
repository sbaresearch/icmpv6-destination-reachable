#General Settings
func=$1
name=$2
iso=$3

echo "Measuring VM: $3 with OS $2"
log_dir="test/timxceeded"
logfile="$log_dir/$name.log"
mkdir -p $log_dir
rm /tmp/debian{.in,.out}
vm_input="/tmp/debian.in"
vm_output="/tmp/debian.out"
mkfifo /tmp/debian{.in,.out}

function prepare_iso {
	iso=$1
	sudo mount -o loop,norock $iso ~/iso_mount
}

function cleanup {
	sleep 1
	sudo umount -d -f ~/iso_mount
	#rm $1
}


function execute_in_vm() {
    command="$1"
    overwrite_verify=$2
    
    verify=true
    if [ ! -z $overwrite_verify ]; then
        verify=$overwrite_verify
    fi
    # Send the command to the VM through the fifo pipe
    echo -e "$command" >> "$vm_input"
    #Wait for command to be executed
    echo "INPUT: $command"
    sleep 1
    root_prompt='root@debian:/home/user#'
    user_prompt='user@debian:~$'
   
    if [ "$verify" = true ]; then
        while true; do
          #Verify if command ended successfully
          last_output=$(tail -n 1 $logfile)
          #echo "$(tail -n 2 $logfile)"
          if [[ "$last_output" == *"${root_prompt}"* || "$last_output" == *"${user_prompt}"* ]]; then
              break
          fi
          #Else check in one second again 
          sleep 1
        done
    fi
}

function spawn_vm() {
    curdir=$(pwd)
    cd ~/iso_mount
    kernel=$(ls "live" | grep "vmlinuz" | head -n 1) #live/vmlinuz -> since bookworm (debian 12) multiple kernel files exist
    initrd=$(ls "live" | grep "initrd" | head -n 1) #live/initrd1.img
    echo $iso
    echo $kernel 
    echo $initrd
    gnome-terminal -- bash -c "kvm -m 1024 -nographic -enable-kvm -boot d -cdrom $iso -kernel "live/$kernel" -initrd "live/$initrd" -append 'console=ttyS0,115200 boot=live live-getty' -netdev bridge,id=hn0,br=br0 -device virtio-net-pci,netdev=hn0,id=nic1 <$vm_input >$vm_output"   
    pid_kvm=$(pgrep -f "kvm")
    # Wait for a moment to ensure the KVM process is ready to accept input
    sleep 20
    echo "VM Started"   

    cd $curdir
}

function establish_fifo_communication(){
    >$logfile
    gnome-terminal -- bash -c "cat /tmp/debian.out >> $logfile"
    pid_outpipe=$(pgrep -f "cat /tmp/debian.out")
    gnome-terminal -- bash -c "cat >> /tmp/debian.in"
    pid_inpipe=$(pgrep -f "cat >> /tmp/debian.in")
    echo "FIFO established"
}

function config_vm(){
    #Change to privileged shell    
    execute_in_vm "sudo su"
    #Enable IPv6 Support and configure static IPv4/IPv6 address
    execute_in_vm "modprobe ipv6" 



    #Depending on major version configure network interface   
    major_version=$(echo $name | cut -d "." -f 1)
    if [[ ${major_version} -ge 9 ]]; then
       #Systemctl now will take longer to restart
       #execute_in_vm "systemctl disable systemd-networkd-wait-online.service"
       #execute_in_vm "systemctl stop systemd-networkd-wait-online.service"

       execute_in_vm "echo -e 'auto ens3\niface ens3 inet static\naddress 192.168.100.10\nnetmask 255.255.255.0\ngateway 192.168.100.1\niface ens3 inet6 static\naddress 2001:db8:ff::100\nnetmask 32\ngateway 2001:db8:ff::1' >/etc/network/interfaces"
        execute_in_vm "ip addr flush dev ens3"
        execute_in_vm "ip link set ens3 down"
        #execute_in_vm "echo '0' > /proc/sys/net/ipv6/icmp/ratelimit"
    else
        execute_in_vm "echo -e 'auto eth0\niface eth0 inet static\naddress 192.168.100.10\nnetmask 255.255.255.0\ngateway 192.168.100.1\niface eth0 inet6 static\naddress 2001:db8:ff::100\nnetmask 32\ngateway 2001:db8:ff::1' >/etc/network/interfaces"
        execute_in_vm "ip addr flush dev eth0"
        execute_in_vm "ip link set eth0 down"    
    fi   
    #Restart Networking to load new config
    execute_in_vm "/etc/init.d/networking restart"
    #Enable IPv4 Forwarding
    execute_in_vm "echo 1 > /proc/sys/net/ipv4/ip_forward"
    #Enable IPv6 Forwarding
    execute_in_vm "sed -i 's/#net.ipv6.conf.all.forwarding/net.ipv6.conf.all.forwarding/g' /etc/sysctl.conf"
    execute_in_vm "sysctl -p /etc/sysctl.conf" 
    
}


function host_routes(){
    sudo chmod 4755 /usr/lib/qemu/qemu-bridge-helper
    sudo ip route add 192.168.100.0/24 via 192.168.100.10
    sudo ip -6 route add 2001:db8:ff::1/32 via 2001:db8:ff::100
    #sudo ip -6 route add 
}

function login() {
    #All except squeezy need to login manually 
    execute_in_vm "user" false
    sleep 0.5
    execute_in_vm "live" false
}

function extract_kernel_version() {
    execute_in_vm "uname -a"
    sleep 1
    kernel_version=$(grep "uname -a" $logfile -A 1 | grep "Linux" | cut -d " " -f 2,3 | sed "s/ /-/g")
    echo "$name,$kernel_version" >> "$log_dir/oskernel.log"
}

function measure_vm() {
    #Perform Measurement
    guest_ip=192.168.100.10
    #Trigger Address Resolution to get the MAC address of the VM from the ip neigh table
    ping $guest_ip -c 1
    vm_mac=$(ip neigh | grep $guest_ip | cut -d " " -f 5)
    #Orchestrate Timxceeded Scan for VM
    ./orchestrate_kvm_scan.sh timxceeded $vm_mac $name
}

function main() { 
	prepare_iso $iso
   
    #Start VM
    establish_fifo_communication
    spawn_vm    

    #Login (Manual login necessary if version > Squeezy)
    login

    #Get Kernel Version
    echo "Extract Kernel Version"
    extract_kernel_version

    #Configure Networking and IP/v4/v6 Forwarding
    echo "Prepare VM for Measurement"
    config_vm
    sleep 1
    #Perform Measurement
    echo "Perform Measurement"
    measure_vm

    #Cleanup by killing additional terminal windows
    kill $pid_inpipe
    kill $pid_outpipe
    kill $pid_kvm
	
	cleanup
}

"$@"
