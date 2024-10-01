#!/bin/bash
#requires: moreutils > sponge; bgpdump (https://github.com/RIPE-NCC/bgpdump, prereq: libbz2-dev
mkdir -p dumps
mkdir -p dumps/v4
mkdir -p dumps/v6

mkdir -p out
mkdir -p out/v4
mkdir -p out/v6

if [[ ! -z "$(ls -A data.ris.ripe.net)" ]]; then
    read -p "Redownload BGP? (y/n): " renew
else
    renew="y"
fi

if [[ $renew == "y" ]]; then
    rm -r data.ris.ripe.net/*
fi

if [[ ! -z "$(ls -A dumps/v6)" ]]; then
 read -p "Extract BGP? (y/n): " extract
else
    extract="y"
fi


for i in `seq 0 24`; 
        do
                file=$(printf %02d $i)
                echo "Processing rrc$file"
                if [[ $renew == "y" ]]; then
                	wget -x data.ris.ripe.net/rrc${file}/latest-bview.gz                                    	
                fi
                if [[ $extract == "y" ]]; then                    
                    gunzip -c data.ris.ripe.net/rrc${file}/latest-bview.gz > data.ris.ripe.net/rrc${file}/latest-bview.txt
                    # ASPATH 10000, 12000, 13000 {13001,13002,13002 } => sed 's/{.*}//g' removes AS-Sets from path => remove if unwanted + remove tailing whitespace s/[ \t]*$//
                    /opt/bgpdump/bgpdump -vm data.ris.ripe.net/rrc${file}/latest-bview.txt | cut -d "|" -f 6,7 | grep "::/" | sed 's/[ \t]*$//' | awk -F '[| ]' '{print $1","$NF}' >  dumps/v6/rrc${file}.txt
                    /opt/bgpdump/bgpdump -vm data.ris.ripe.net/rrc${file}/latest-bview.txt | cut -d "|" -f 6,7 | grep -v "::/" | sed 's/[ \t]*$//' | awk -F '[| ]' '{print $1","$NF}'  >  dumps/v4/rrc${file}.txt
                 
                    rm data.ris.ripe.net/rrc${file}/latest-bview.txt
                 fi 
		done

out="out/v6/bgp_with_as.txt"
for file in $(ls -1 ./dumps/v6/*.txt); do cat "$file" >> $out; done; wc -l $out; sort -u $out | sponge $out; wc -l $out

out="out/v4/bgp_with_as.txt"
for file in $(ls -1 ./dumps/v4/*.txt); do cat "$file" >> $out; done; wc -l $out; sort -u $out | sponge $out; wc -l $out


#Save space on disk
tar -zcvf dumps.tar.gz dumps
rm -R dumps
#
tar -zcvf data.ris.ripe.net.tar.gz data.ris.ripe.net
rm -R data.ris.ripe.net
#use tar -xf <filename> to extract
