source scan.conf

scan(){

	
	outdir="output_dir"
	scan_proto="icmpv6"
	scan_date=$(date '+%Y_%m_%d')
	speed="45000"
	
	echo "Scanning $scan_proto with $speed pps"
	#Outputdir
	mkdir -p $outdir/$scan_date/
	
	target_shuffle_files=$(ls <path to shufled input files>/targets_shuf.txt.*)
	
	for target_file in $target_shuffle_files ; do
		echo $target_file
		fname=$(basename "$target_file")
		scanned_target_file="$outdir/$scan_date/${fname}_scanned.txt"
		renew_scan="y"

		if [[ $renew_scan = "y" ]]; then
			if [[ $scan_proto == "icmpv6" ]];then
				$zmap -M "icmp6_echoscan_time" --ipv6-source-ip "$ip" -r "$speed" -G "$gw" --ipv6-target-file "$target_file" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_target_file" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
			fi
		fi

	done 
	
}

scan
