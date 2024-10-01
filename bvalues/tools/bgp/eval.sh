#!/bin/bash

#Download IP network data from BGP tables.
#Parameters: <date of format: yyyy-mm-dd>

date=$1
currentdir=$(pwd)
bgp_ris="$currentdir/BGP/RIS/$date/"

function main(){

	#Verify by user before entering function
	read -p "Download and extract BGP RIS data (y/n)" renew_bgp_ris
	if [[ $renew_bgp_ris = "y" ]]; then
		mkdir -p $bgp_ris
		echo $bgp_ris	
		cd $bgp_ris
		../../tools/bgp/extract_bgp.sh
	fi	
}

main
