#
# Persistent SSH Connection accross multiple commands
#
user=$1
target=$2
logname=$3
measurement=$4
duration=$5


host="$user@$target"

tmp_dir=$(mktemp -d "/tmp/$(basename "$0").XXXXXX")
ssh_control_socket="$tmp_dir/ssh_control_socket"

# Setup control master
echo $(date)": Initiating SSH Master socket to $host; CMD duration $duration"
ssh -i ~/.ssh/id_docker -f -N -o 'ControlMaster=yes' -o 'StrictHostKeyChecking no' -S $ssh_control_socket $host 
remote_cmd="ssh -o LogLevel=QUIET -S $ssh_control_socket $host"

outfile="measurement/ndrequests/${measurement}/${target}_${logname}.log"
date +"%T.%3N" > $outfile
out=$($remote_cmd "time timeout 30 tcpdump -nv 'icmp6 && ip6[40] == 135'")
echo "$out" >> $outfile


#router-solicitation: 133
#router-advertisement: 134
#neighbor-solicitation: 135
#neighbor-advertisement: 136

#Close Connection
echo $(date)": Exiting SSH Master socket to $host"
ssh -S "$ssh_control_socket" -O check $host
ssh -S "$ssh_control_socket" -O exit $host














