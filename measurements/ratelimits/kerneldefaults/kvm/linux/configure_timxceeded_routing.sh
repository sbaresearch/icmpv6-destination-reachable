#Add this to netplan

sudo ip route add 192.168.100.10/18 dev br0
sudo ip -6 route add 2001:db8:ff::1/48 via 2001:db8:ff::100
