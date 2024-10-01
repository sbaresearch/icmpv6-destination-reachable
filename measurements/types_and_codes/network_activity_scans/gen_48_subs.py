import argparse
from tqdm import tqdm

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1
    
def get_subnets(base_address, subnet_count=2**16):
	# Extract the prefix and remove trailing '::' if it's there
	prefix = base_address.split("::")[0]
	subnets = ""
	if prefix.count(":") != 2:
		prefix_blocks=prefix.split(":")
		# Calculate how many blocks we need to fill to reach the :xxxx part
		missing_blocks = 3 - len(prefix_blocks)
		# Fill missing blocks with '0'
		for _ in range(missing_blocks):
			prefix_blocks.append('0')
		prefix = ':'.join(prefix_blocks)
	
	# Generate all possible subnets by changing the next 16 bits
	host_id = "ca73:e6a7:5529:fde4"
	for i in range(subnet_count):
		subnet = f"{prefix}:{i:04x}:{host_id}"
		subnets+="\n"+subnet
	return subnets

def main():
	"""
		Input: List of networks, Output: New random Addresses in each network, Nr Addr = Number of new addresses for each network
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--inputfile", required=True, type=str, help="File with IPv6 Prefixes")
	parser.add_argument("-s", "--subnetsize", required=False, type=int, default=64, help="Subnetprefix up to which addresses are generated")
	parser.add_argument("-o", "--outputfile", required=False, type=str, default="ipv6targets.txt" ,help="File to dump addresses")
	parser.add_argument("-b", "--blocklist", required=False, type=str, default="/etc/scanning/blocklist", help="File with blocked IP ranges")
	args=parser.parse_args()
	
	nr_prefixes=file_len(args.inputfile)
	#blocklist=parse_blocklist(args.blocklist)
	with open(args.outputfile,'w') as f_out:
		with open(args.inputfile,'r') as f_in:
			for line in tqdm(f_in, total=nr_prefixes):
				line=line.strip()
				subnets=get_subnets(line)
				f_out.write(subnets+"\n")


if __name__== "__main__":
	main()
