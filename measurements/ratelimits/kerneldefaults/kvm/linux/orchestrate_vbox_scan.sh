# Scan non-allocated addresses in a routed subnet to trigger nd cache/queue exhaustion
routerid=$1 #0-f (Router IDs, see Routerlab documentation)
gw=$2 #(MAC of Routerinterface connected to the Vantage point)

# 1) Prepare Target address

#IPv4 Settings
src4="192.168.56.1"
target4="192.168.4.1"

#IPv6 Settings
src6="$(ip -6 a | grep tap0 -A 1 | grep inet6 | sed 's/^ *//g' | cut -d ' ' -f 2 | cut -d '/' -f 1)" 
target6="2001:db8:$routerid:1::1"

pps=( "200"  ) #"50000"
duration="20"
interface="vboxnet0"

measurements=$3
name=$4


if [[ $measurements == "all" ]]; then
	measurements=( "addr" "noroute" "timxceeded" )
else
	measurements=( $3 )
fi

for measurement in ${measurements[@]};do

	if [[ $measurement == *"addr"* ]]; then
		dest="1"
		ttl=10
		track_nd=1
	elif [[ $measurement == *"noroute"* ]]; then
		dest="6"
		ttl=10
		track_nd=0
	elif [[ $measurement == *"timxceeded"* ]] ;then
		dest="1"
		ttl=1
		track_nd=0
	fi
	
	outdir="measurement/$4/${measurement}/"
	
	mkdir -p $outdir
	
	if [[ $track_nd == 1 ]]; then
		ssh-keygen -f "~/.ssh/known_hosts" -R $target
	fi
	#Generating Targets
	echo "Generating Targets"
	#scaninput="scaninput.txt"
	#time sed -i "s/2001:db8:.\{1,2\}:.\{1\}:/2001:db8:$routerid:$dest:/g" $scaninput
	
	#Write addr x times to file
	scaninput="scaninput_single.txt"
	total_addr=$(( 20 * 200 ))
	x=1
	target="2001:db8:$routerid:$dest::1"
	while [ $x -le $total_addr ] ; do 
		var+="$target\n"
		x=$(( $x + 1 )) 
	done
 	#First store x lines in memory, then perform a single file operation for better performance
	echo -ne $var > $scaninput



	# Measurement
	for scanrate in "${pps[@]}"; do
		
		if [[ $track_nd == 1 ]]; then
			echo "PPS: $scanrate - Starting collector on measurement host"
			outfile="$outdir/${target}_${scanrate}.log"
			date +"%T.%6N" > $outfile
			ssh -i ~/.ssh/id_docker -o 'StrictHostKeyChecking no' user@$target "timeout 20 tcpdump -nv 'icmp6 && ip6[40] == 135'" >> $outfile &
			#bash ./master_socket_ssh_nd_requests.sh "user" $target $scanrate $outdir $duration&
			#record_pid=$!
		fi

		echo "PPS: $scanrate - Start scan"
		#starttime=$(date +"%H:%M:%S")	
		#SCAN IPV4
		./aim_zmap_reqnr_single/src/zmap -M "icmp_echo_time" -S $src4 -r $scanrate --probe-ttl $ttl -G "$gw" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outdir/rec_${target}_${scanrate}.log" --disable-syslog --output-filter="success = 0 || success = 1" -i $interface --ignore-blacklist-errors $target4 -v 5 -b blacklist.txt -w whitelist.txt
	
		#SCAN IPV6  
		#./aim_zmap_reqnr/src/zmap -r $scanrate -M "icmp6_echoscan_time" --probe-ttl $ttl --ipv6-source-ip "$src6" -G "$gw" --ipv6-target-file $scaninput --output-fields="nrsent,orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outdir/rec_${target}_${scanrate}.log" --disable-syslog --output-filter="success = 0 || success = 1" -i $interface

		#sed -i "1s/.*/$starttime/" "measurement/ndrequests/${measurement}/rec_${target}_${scanrate}.log
		echo "Scan complete"
		
		#if [[ $track_nd == 1 ]]; then
		#	wait $record_pid
		#fi

	done

done
