source scan.conf
file=$1
title=$2

scan(){
	scan_proto=$1
	scan_date=$(date '+%Y_%m_%d')

	echo "Scanning $scan_proto"
	mkdir -p $outdir/$title/$scan_date/$scan_proto
	echo "$outdir/$title/$scan_date/$scan_proto"
	target_shuffle_file="$outdir/$title/$scan_date/$scan_proto/targets.txt"
	scanned_target_file="$outdir/$title/$scan_date/$scan_proto/scanned_targets.txt"
	
	#Take input file, shuffle it to random order, place it in output folder
	shuf $file -o $target_shuffle_file
	
	if [[ -f "$scanned_target_file" ]]; then
		read -p "Scan File already exists, overwrite? (y/n)" renew_scan
	else
		renew_scan="y"
	fi

	if [[ $renew_scan = "y" ]]; then
		if [[ $scan_proto == "icmpv6" ]];then
			$zmap -M "icmp6_echoscan_time" --ipv6-source-ip "$ip" -r "$speed" -G "$gw" --ipv6-target-file "$target_shuffle_file" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_target_file" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
		elif [[ $scan_proto == "tcp" ]];then
			port="443"
			$zmap -M "ipv6_tcp_synscan_time" -p "$port" --ipv6-source-ip "$ip" -r "$speed" -G "$gw" --ipv6-target-file "$target_shuffle_file" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_target_file" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
		elif [[ $scan_proto == "tcp_ack" ]];then
			$zmap -M "ipv6_tcp_ackscan_time" -p "$port" --ipv6-source-ip "$ip" -r "$speed" -G "$gw" --ipv6-target-file "$target_shuffle_file" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_target_file" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
		elif [[ $scan_proto == "udp" ]];then
			port="53"
			$zmap -M "ipv6_udp_time" -p "$port" --ipv6-source-ip "$ip" -r "$speed" -G "$gw" --ipv6-target-file "$target_shuffle_file" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_target_file" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
		fi
	fi

	python3 rtt.py $scanned_target_file tmpfile

}


main(){
	skip=0
	if [[ $skip == 0 ]];then
		echo "Start scans"
		# Scan Targets
		if [[ $proto == "all" ]]; then
			type=( icmpv6 tcp tcp_ack udp ); for i in "${type[@]}"; do			
				scan $i
			done
		else
			read -p "Do you want to scan $proto (y/n)" scan
			if [[ $scan = "y" ]]; then
				scan $proto
			fi
		fi
	fi

}


main
