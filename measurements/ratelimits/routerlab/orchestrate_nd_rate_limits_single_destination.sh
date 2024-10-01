# Scan non-allocated addresses in a routed subnet to trigger nd cache/queue exhaustion
routerid=$1 #0-f (Router IDs, see Routerlab documentation)
gw=$2 #(MAC of Routerinterface connected to the Vantage point)
measurements=$3
name=$4
scanrate=$5
duration=$6

#scanrate="200"
# 1) Prepare Target address
src="$(ip -6 a | grep tap0 -A 1 | grep inet6 | sed 's/^ *//g' | cut -d ' ' -f 2 | cut -d '/' -f 1)" 
 #"50000"

interface="tap0"

total_addr=$(( duration * scanrate ))


if [[ $measurements == "all" ]]; then
	measurements=( "addr" "noroute" "timxceeded" "echo")
else
	measurements=( $3 )
fi

for measurement in ${measurements[@]};do
	if [[ $measurement == *"echo"* ]]; then
		target="2001:db8:$routerid:1::1"
		dest="1"
		ttl=10
		track_nd=0
	elif [[ $measurement == *"addr"* ]]; then
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
	target="2001:db8:$routerid:$dest::1"

	
	outdir="measurement/$4/${measurement}/"
	
	mkdir -p $outdir
	
	if [[ $track_nd == 1 ]]; then
		ssh-keygen -f "~/.ssh/known_hosts" -R $target
	fi
	#Generating Targets
	echo "Generating Targets"

	scaninput="input/scaninput.txt"
	tmpscaninput="input/tmp.txt"
	> $tmpscaninput
	
	
	if [[ $measurement == *"addr"* ]]; then
		time head -n $total_addr $scaninput | sed "s/2001:db8:.\{1,2\}:.\{1\}:/2001:db8:$routerid:$dest:/g" > $tmpscaninput
	else

		#Write addr x times to file		
		x=1
		var=""
		echo $target
		while [ $x -le $total_addr ] ; do 
			var+="$target\n"
			x=$(( $x + 1 )) 
		done
 		#First store x lines in memory, then perform a single file operation for better performance
		echo -ne $var > $tmpscaninput
		echo "Target Generation Complete"
	fi

	# Measurement
	if [[ $track_nd == 1 ]]; then
		echo "PPS: $scanrate - Starting collector on measurement host"
		outfile="$outdir/${target}_${scanrate}_${duration}.log"
		date +"%T.%6N" > $outfile
		ssh -i ~/.ssh/id_docker -o 'StrictHostKeyChecking no' user@$target "timeout 10 tcpdump -nv 'icmp6 && ip6[40] == 135'" >> $outfile &
	fi

	echo "PPS: $scanrate - Start scan"	  
	outfile="$outdir/rec_${target}_${scanrate}_${duration}.log"
	if test -f "$outfile"; then
		i=1
    	while true; do
    		outfile="$outdir/rec_${target}_${scanrate}_${duration}$i.log"
			if ! test -f "$outfile"; then
	    		break
	    	fi
	    	i=$((i+1))
    	done
	fi
	
	./zmap_reqnr_single/src/zmap -r $scanrate -M "icmp6_echoscan_time" --probe-ttl $ttl --ipv6-source-ip "$src" -G "$gw" --ipv6-target-file $tmpscaninput --output-fields="nrsent,orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outfile" --disable-syslog --output-filter="success = 0 || success = 1" -i $interface -c 1

	echo "Scan complete"
	sleep 3


done
