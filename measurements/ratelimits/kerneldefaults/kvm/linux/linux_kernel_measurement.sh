#This script includes several components, from downloading the ISOs to running them in KVM and preparing them for the measurement

extract_urls="grep -o '<a .*href=.*>' | sed -e 's/<a /\\n<a /g' | sed -e 's/<a .*href=['\"'\"'\"]//' -e 's/[\"'\"'\"'].*$//' -e '/^$/ d'"
isodir="/opt/isos"
mkdir -p "$isodir"

# Downloads a debian kernel from 
function download {
	debian_live_cds=( $(curl -s https://cdimage.debian.org/mirror/cdimage/archive/ | grep live |  grep indexcolname | bash -c "$extract_urls" | sort -u |  sort -t. -k1,1n -k2,2n -k3,3n | grep "\." | tr -d "/") )
	
	for version in "${debian_live_cds[@]}"; do
			#Check if no measurement for this iso exists
  			if [ -f "measurement/timxceeded/${version}.log" ]; then
  				echo "$version: already measured"
  				continue
  			fi

  			#Skip Squeeze and Wheezy as live console does not work on them
			squeeze="^6."
			wheezy="^7."
			#stretch="^9." #No standard.iso available
  			if grep -q "$squeeze" <<< "$version" || grep -q "$wheezy" <<< "$version"; then #|| grep -q "$stretch" <<< "$version"; then
  				echo "$version: not supported"
  				continue
  			fi


			possible_paths=( "iso-cd" "iso-hybrid" )
			for iso_path in "${possible_paths[@]}"; do
				#urlpath="https://cdimage.debian.org/mirror/cdimage/archive/${version}amd64/$iso_path/"
				urlpath="https://cdimage.debian.org/mirror/cdimage/archive/${version}/amd64/${iso_path}/"
  				stretch="^9."
  				#Stretch was built differently, thus no standards.iso is avialable. We have to download the full 2GB gnome.iso
  				if grep -q "$stretch" <<< "$version"; then
  					result=$(curl -s  $urlpath | bash -c "$extract_urls" | sort -u)
  					iso_file=$(echo "$result" | grep "gnome.iso$")
  				else					
  					result=$(curl -s  $urlpath | bash -c "$extract_urls" | sort -u)
  					iso_file=$(echo "$result" | grep "standard.iso$")
  				fi
  				if [ ! -z "$iso_file" ]; then  					
  						echo $iso_file
  						target_vm="$isodir/$iso_file"
  						#Check if iso was already downloaded
  						if [ ! -f "$target_vm" ]; then
  							echo "Downloading ISO"
  							wget -4 --quiet -P $isodir "${urlpath}${iso_file}"
						fi
  						
  						#prepare_iso $target_vm
  						./fifo_vm_serial.sh main $version $target_vm
  						#cleanup $target_vm
  						break
  					
  				else
  					echo "$version - $iso_path: failed"
  				fi

  				#Delete if disk space is low
  				#if [ -f "$target_vm" ]; then
  				#	rm $target_vm
  				#fi
			done
	done
}



function main {
	download
}

main
