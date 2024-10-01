lastbit_input=$1
bvalue_input=$2


function scan(){
	# Scan LastBit
	curdir=$(pwd)
	cd "tools"
	## Zmap
	./scan_zmap.sh "$lastbit_input" "lastbit"
	
	# Scan BValues
	./scan_zmap.sh "$bvalue_input" "bvalues"

	cd $curdir
}


scan




