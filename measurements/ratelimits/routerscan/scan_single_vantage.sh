#!/bin/bash

# Read Scan Configuration
source scan_full.conf
#required fields: ip,mac,gw,int,speed,outdir,zmap

usage() { echo "Usage: $0 [-p ( Perform ping measurement) -b (Perform banner grabbing) -r (Perform rate limit measurement) -t (Path to addresslist) -f (Force scan)]" 1>&2; exit 1; }

#Assign parameters to shell variables
while getopts ":p:b:r:t:f:" o; do
    case "${o}" in
       p)
            pingflag=${OPTARG}
            ;;
       b)
	       	bannerflag=${OPTARG}
            ;;
       r)
        	rateflag=${OPTARG}
            ;;            
       t)
            targets=${OPTARG}
            ;;
       f)
            forceflag=${OPTARG}
            ;;     
       *)  
            usage
            ;;
       esac
done

#After the shift $1 points to the first non-option argument after getopts
shift "$((OPTIND-1))"

#Verify if parameters were set, else print usage
if ([[ -z "${targets}" ]]); then
    usage
    exit 1
fi

#Global vars
run=$(date '+%Y-%m-%d')
outdir="<specify outdir>"
echo $outdir
mkdir -p $outdir

# Needed for Ping an Banner Grabbing
router_addrfile="$outdir/routeraddr.txt"
scanned_router_addrfile="$outdir/ping.csv"
banner_router_addrfile="$outdir/banners.csv"
scanrate_ping=2000
scanrate_rate=200
duration_rate=10 # Total amount of seconds to fingerprint error message behavior
duration_twovantage_rate=10
vantages=( $ip ) 

function perform_ping(){ 
        if [[ ! -f $scanned_routeraddrfile ]]; then
	        $zmap -M "icmp6_echoscan_time" --ipv6-source-ip "$ip" -r "$scanrate_ping" -G "$gw" --ipv6-target-file "$router_addrfile" --output-fields="orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$scanned_router_addrfile" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1"
		fi
}

function perform_banner(){
    cat $router_addrfile | zgrab2 multiple -c zgrab.ini -o $banner_router_addrfile --source-ip "$ip"
}

function precheck(){
	check_ping=-1
	#echo "$src,$target,$hops"
	res=$(ping -c 1 -t "$hops" -w 3 "$target")
	
	#Perform Single Ping Check, if it succeeds, we can skip further checks
	if $(echo "$res" | grep -q "From"); then
		#echo "$res"	
		responder=$(echo "$res" | grep "From" | cut -d " " -f 2)
		#echo "$responder"
		code=$(echo "$res" | grep "From" | cut -d " " -f 4)
		#echo "$code"
		if [[ "$responder" == "$src" ]]; then
			check_ping=0
			#echo "$src <- $target: check success"
		fi
	fi

	if [[ $check_ping -eq -1 ]];then
		#Perform Paris Traceroute with min hop =3
		res=$(paris-traceroute -f=$hops -m=25)
	fi

	
}
function measure_addr(){
	src=$1
	target=$2
	hops=$3
	scanid=$4
	completed_actions=$5
	vantage_id=1
	inputfile="zmap_input/${scanid}.txt"
	outputfile="$outdir/zmap_output/${src}_single.csv"
	mkdir -p "$outdir/zmap_output/"

	#Write addr x times to file
	total_addr=$((duration_rate*scanrate_rate))
	x=1
	while [ $x -le $total_addr ] ; do 
		var+="$target\n"
		x=$(( $x + 1 )) 
	done
 	#First store x lines in memory, then perform a single file operation for better performance
	echo -ne $var > $inputfile

	echo "$completed_actions Scanning $src with dest $target at hop $hops"

	#Scan 10 seconds with main vantage point 
	#> "zmap_debug/${src}.log"
	$zmap -M "icmp6_echoscan_time" --ipv6-source-ip "$ip" --probe-ttl "$hops" -r "$scanrate_rate" -G "$gw" --ipv6-target-file "$inputfile" --output-fields="nrsent,orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outputfile" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1" --quiet -c 1 &> /dev/null 

	#Scan 10 Seconds with 2 Vantage Addresses
	#for ipaddr in ${vantages[@]}; do
	#	vantagefile="zmap_input/${scanid}_${vantage_id}.txt"
	#	cp $inputfile $vantagefile
	#	outputfile="$outdir/zmap_output/${src}_vantage_${vantage_id}.csv"
	#	$zmap -M "icmp6_echoscan_time" --ipv6-source-ip "$ipaddr" --probe-ttl "$hops" -r "$scanrate_rate" -G "$gw" --ipv6-target-file "$vantagefile" --output-fields="nrsent,orig-dest-ip,classification,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str" --output-module "csv" -o "$outputfile" -i "$int" --disable-syslog --output-filter="success = 0 || success = 1" -c 1 --quiet &> /dev/null 
	#	vantage_id=$((vantage_id + 1))
	#done
	#wait
}

function perform_rate(){
	mkdir -p "zmap_input"

	parallel_actions=20
	total_actions=$(($(wc -l $targets | cut -d " " -f 1) -1))
	remaining_actions=$total_actions
	completed_actions=0
	destination_hop_ary=()
	
	echo "Reading Targets"
	mapfile destination_hop_ary < <(tail -n +2 $targets)

	echo "Start scanning"
	while [ $remaining_actions -gt 0 ]; do	
		#Do a maximum of $parallel_actions, reduce to leftover_actions in the last cycle
		leftover_actions=$((remaining_actions>parallel_actions ? parallel_actions : remaining_actions))  	
		nr_actions=0
		#Initiate scan for parallel_actions
		start=`date +%s`
		while [ $nr_actions -lt $leftover_actions ]; do
			addr_pair=${destination_hop_ary[$completed_actions]}
			IFS=, read -r src count target hops < <(echo $addr_pair)
			hops=$(echo -n $hops | tr -d "\r" | tr -d "\n")
			measure_addr $src $target $hops $nr_actions $completed_actions &
			process_id=$!

			nr_actions=$((nr_actions + 1))
			completed_actions=$((completed_actions + 1))
			remaining_actions=$((remaining_actions - 1))
		
		done

		#Wait for parrallel_actions to complete for starting next round
		wait
		end=`date +%s`
		echo Round Complete in `expr $end - $start` seconds!
	done
	
}


function main(){
	#Extract router hitlist src addresses
	if [[ ! -f $router_addrfile ]] || [[ ! -z $forceflag ]]; then
		tail -n +2 $targets | cut -d "," -f 1 > $router_addrfile
	fi
	
    #Perform ping measurement
    if [[ ! -z $pingflag ]]; then
        perform_ping
    fi 

	#Perform banner grabs
	if [[ ! -z $bannerflag ]]; then
  		perform_banner
  	fi
  	
  	if [[ ! -z $rateflag ]]; then
  		perform_rate
  	fi 
}


# Call main function with all parameters
main "$@"
