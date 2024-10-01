#python3 generate_addr.py <input-file> <output-file>
# input_format: <IPv6Network>\n <IPv6Network>
import sys
import ipaddress
from bitstring import BitArray
import random
from pprint import pprint
import os
import math
from tqdm import tqdm


def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def return_all_hosts(net):
	"""
		hosts() => Returns an iterator over the usable hosts in the network. The usable hosts are all the IP addresses that belong to the network, except the Subnet-Router anycast address. For networks with a mask length of 127, the Subnet-Router anycast address is also included in the result.
	"""
	ip_nets=map(str,list(ipaddress.IPv6Network(net).hosts()))
	return ip_nets
	

def generate_addr(addr,nr_addr,network_border,subnet_border,f_out):
	"""
	 Generate Nr_Addr of random IPv6 Addresses for one Network Address
	"""
	subnet_bits= subnet_border-network_border
	if subnet_bits > 34:
		return 0

	ip_orig=BitArray(bytes=ipaddress.IPv6Address(addr).packed)
	rand_bits=128-subnet_border
	mask = BitArray(bin="1"*network_border+"0"*(subnet_bits+rand_bits))
	addr = ip_orig & mask

	subnet_space=2**(subnet_border-network_border)
	
	new_addr=0
	
	while new_addr<subnet_space:
			new_val = int(random.getrandbits(rand_bits))
			mask = BitArray(bin="0"*network_border + BitArray(uint=new_addr, length=subnet_bits).bin +BitArray(uint=new_val, length=rand_bits).bin)
			new  = addr ^ mask
			ip = ipaddress.IPv6Address(int(new.bin,2))
			f_out.write(str(ip)+"\n")
			new_addr+=1
	return new_addr


def do (f_in,f_out,nr_addr):
	"""
		Write Nr_Addr new Addresses with format /x bits taken from the input network and y random bits: x + (128-x) * y bits to output file
	"""
	print("Generating Addresses")
	in_len=file_len(f_in)
	f_in = open(f_in, 'r+')
	f_out= open(f_out, 'w')
	addr_count=0
	net_count=0
	for line in tqdm(f_in, total=in_len):
			#print(net)
			line=line.strip().split(",")
			net=line[0]


			network_border=int(net.split("/")[1])
			subnet_border=int(line[2])
			addr=net.split("/")[0]
			new_addr=generate_addr(addr,nr_addr,network_border,subnet_border,f_out)
			if new_addr==0:
				print("Network too large: "+net)
				continue
			addr_count+=new_addr
			net_count+=1
	print("Finished - "+str(addr_count)+" addresses were generated!")
	print(str(net_count)+" Network covered!")
	f_in.close()
	f_out.close()

def main():
	"""
		Input: List of networks, Output: New random Addresses in each network, Nr Addr = Number of new addresses for each network
	"""
	input_file = sys.argv[1]
	output_file = sys.argv[2]
	nr_addr="all"


	do(input_file,output_file,nr_addr)

if __name__== "__main__":
	main()
