#! /bin/zsh


if [ "$(id -u)" -ne 0 ]
  then echo "Please run as root"
  exit
fi

ip link set dev tap0 up
ip address add 2001:db8:b000:b::2/64 dev tap0
for i in {1..15};do
	x=$(printf "%x" $i)
	ip route add 2001:db8:$x::/48 via 2001:db8:b000:b::100$x 
done
#ip route add 2001:db8:2::/48 via 2001:db8:b000:b::1002

#via 2001:db8:a000:a::1
