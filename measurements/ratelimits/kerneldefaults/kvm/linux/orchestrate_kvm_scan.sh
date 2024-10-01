# Trigger Timexceeded, No Route and Addr Unreachable Messages

measurements=$1 #("timxceeded noroute addr or all")
gw=$2 #(MAC of VM Interface)
name=$3 #(Name of output folder e.g. Kernel, OS version)


#IPv4 Settings
src4="192.168.100.1"
target4="192.168.100.11"
scaninput4="scaninput_single4.txt"
	
#IPv6 Settings
src6="$(ip -6 a | grep br0 -A 1 | grep inet6 | sed 's/^ *//g' | cut -d ' ' -f 2 | cut -d '/' -f 1)" 
target6="2001:db8:ff::101"
scaninput6="scaninput_single6.txt"

#General Settings
pps=( "200"  ) #"50000"
duration="10" # in seconds
interface="br0"

if [[ $measurements == "all" ]]; then
	measurements=( "addr" "noroute" "timxceeded" )
else
	measurements=( $measurements )
fi

for measurement in ${measurements[@]};do

	if [[ $measurement == *"addr"* ]]; then
		ttl=10
		track_nd=0
	elif [[ $measurement == *"noroute"* ]]; then
		ttl=10
		track_nd=0
	elif [[ $measurement == *"timxceeded"* ]] ;then
		ttl=1
		track_nd=0
	fi

	#Prepare Resultdirectory
	outdir4="test/${measurement}/v4"
	outdir6="test/${measurement}/v6"
	mkdir -p $outdir4
	mkdir -p $outdir6
	#Generating Targets	
	#First store x lines in memory, then perform a single file operation for better performance
	echo "Generating Targets"
	total_addr=$(( duration * pps ))
	x=1
	while [ $x -le $total_addr ] ; do 
			var4+="$target4 "
			var6+="$target6\n"
			x=$(( $x + 1 )) 
	done
 		
	#Write addr x times to file
	#echo -ne $var4 > $scaninput4
	echo -ne $var6 > $scaninput6

	

	# Measurement
	for scanrate in "${pps[@]}"; do
		echo "PPS: $scanrate - Start scan"
		
		#SCAN IPV4
		echo "Scan IPv4"
		./zmap_reqnr_single/src/zmap -M "icmp_echo_time" -S $src4 -r $scanrate --probe-ttl $ttl -G "$gw" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outdir4/rec_${name}_${scanrate}.log" --disable-syslog --output-filter="success = 0 || success = 1" -i $interface --ignore-blacklist-errors -b blacklist.txt -w whitelist.txt -t 10 -c 1
	
		#SCAN IPV6 
		echo "Scan IPv6" 
		./zmap_reqnr_single/src/zmap -r $scanrate -M "icmp6_echoscan_time" --probe-ttl $ttl --ipv6-source-ip "$src6" -G "$gw" --ipv6-target-file $scaninput6 --output-fields="nrsent,orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outdir6/rec_${name}_${scanrate}.log" --disable-syslog --output-filter="success = 0 || success = 1" -i $interface -c 1

		echo "Scan complete"
	

	done

done
