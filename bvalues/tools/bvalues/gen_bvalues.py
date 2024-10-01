# ----------- IMPORTS -----------
import argparse
import sys
import ipaddress
from bitstring import BitArray
import random
from pprint import pprint
import os
import math
from treelib import Tree,Node
from tqdm import tqdm
import time
try:
	import SubnetTree
except Exception as e:
	print(e, file=sys.stderr)
	print("Use `pip install pysubnettree` to install the required module", file=sys.stderr)
	sys.exit(1)

# ----------- HELPER FUNCTIONS -----------
def column(matrix, i):
	return [row[i] for row in matrix]

def bgp_to_subnettree(tree, file, suffix=None):
	with open(file,'r') as fh:
		for line in fh:
			line = line.strip().split(",")[0]
			try:
				tree[line] = line
			except ValueError as e:
				print("Skipped line '" + line + "'", file=sys.stderr)
	return tree

# ----------- BVALUE STEPS -----------
def bvalue_steps_for_network(f_out,addr,bits,nr_addr,stop,network_border=None):
	
	# Require stop-start to be a multiple of bit length, thus we increase the network_border (start) until it is
	start=network_border
	for x in range(network_border, stop):
		if (stop-x) % bits == 0:
			start=x
			break
	
	# Bits to network border 
	ip_orig=BitArray(bytes=ipaddress.IPv6Address(addr[0]).packed).bin[:start]	
	to_go=stop

	# Change every ip to bin => Method 1: 0.000103950500488281250s
	addr=[(bin(int(ipaddress.IPv6Address(ip)))[2:to_go]+"0"*bits).zfill(128) for ip in addr] #.00009512901s 
	addr=list(set(addr))
	
	# Init Variables for BValue Steps comparisson of similar address parts of multiple IPV6 addresses for one network
	to_comp=[]
	to_comp_addr=[]

	# Take Bit steps and look for differences	
	x=start
	while x < to_go:
		addr_part=[h[x:x+bits] for h in addr]
		to_comp.append(addr_part)
		x+=bits

	# Create Tree
	#0100000000000010001001000010000
	#└── 00010000
	#    └── 00000001
	#        ├── 00000000
	#        │   ├── 00000000
	#        │   │   └── 00000001
	#        │   │       └── 00000000
	#        │   │           └── 00000000
	#        │   │               └── 00000000
	#        │   │                   └── 00000000
	#        │   │                       └── 00000000
	#        │   │                           └── 00000000
	#        │   │                               ├── 00000000
	#        │   │                               └── 00000010
	#        │   └── 00000010
	#        │       └── 00010000
	#
	
	#start_time = time.time()
	addr_tree=Tree()
	addr_tree.create_node(ip_orig,ip_orig)
	for i in range(len(to_comp[0])):
		col=column(to_comp,i)
		oldEl=ip_orig
		path=ip_orig
	
		for el in col:
			path+="/"+el
			#print(addr_tree.get_node(path))
			if not addr_tree.get_node(path):
				addr_tree.create_node(el,path,parent=oldEl)
			oldEl=path

	#Output of creating addr 
	# 00100000000000010001001000010000
	# 0010000000000001000100100001000000010000
	# 001000000000000100010010000100000001000000000001
	# 00100000000000010001001000010000000100000000000100000000
	# 00100000000000010001001000010000000100000000000100000101
	# 00100000000000010001001000010000000100000000000100000110
	addr_list=[]
	for node in addr_tree.expand_tree():
   		addr_list.append(addr_tree[node].identifier.replace("/",""))
	addr_list=sorted(addr_list, key=len)
	
	#Create addr for each of above
	total_created=0
	for addr in addr_list:
		start=len(addr)
		rand_bits=128-start
		new_addr={}
		nr_created=0
		while nr_created < nr_addr:
				new_val=int(random.getrandbits(rand_bits))
				new = BitArray(bin=addr + BitArray(uint=new_val, length=rand_bits).bin)
				ip = ipaddress.IPv6Address(new.tobytes())
				if ip not in new_addr:
					f_out.write(str(ip)+"\n")
					new_addr[ip]=1
					nr_created+=1	
		total_created+=nr_created
	
	# Return the number of created addresses		
	return total_created

def collect_addresses_per_net(inputfile,subnettree):
	"""
		Go through the input file of IPv6 Addresses, perform LPM and collect addresses per routed network
	"""
	network_addr_dict={}
	addr_count=0
	with open(inputfile,'r') as f_in:
		# Also support input files of csv format, the ip has to be in the first column, otherwise choose a different column	
		
		for i,line in enumerate(f_in):
			line=line.rstrip("\n").split(",")[0]
			try:
				net=subnettree[line]
			except:
				print("BGP LOOKUP  failed for: "+str(line))
				continue
			addr_count+=1					
			if net not in network_addr_dict:
				network_addr_dict[net]=[]
			network_addr_dict[net].append(line)
	return network_addr_dict


def iterate_and_generate_bvalues(inputfile,routedfile,outputaddr,outputprefixes,bits,nr_addr,stop):
	"""
		Reads routed prefixes, iterates over inputfile of IPv6 addresses, looks up their network performing a longest-prefix-match and generates BValues for all the Addresses of a network 
	"""
	# Track networks sizes that are announced in BGP but are too specific to iterate the subnet space with bvalues, for those networks BValue Steps are not required
	# Track the number of generated addresses
	network_border_error=0
	addr_generated=0

	# Store routed network borders in SubnetTree
	tree = SubnetTree.SubnetTree()
	tree = bgp_to_subnettree(tree, routedfile)

	# Track the current time, set the networks that  is curently handeled to None and create an array for 
	start_time = time.time()
	oldKey = None

	# Collect the addresses per routed network
	net_dict=collect_addresses_per_net(inputfile,tree)

	# Iterate the networks and their input addresses
	with open(outputaddr,'w') as f_out:
		with open(outputprefixes,'w') as f_nets:
			for net,net_addr in tqdm(net_dict.items(),total=len(net_dict)):
				network_border=int(net.split("/")[1])

				# We cannot perform and it does not make sense to perform BValue Steps for networks more specific than stop (120) 
				if network_border>(stop-bits) or network_border==0:
					network_border_error+=1
					continue

				# Write the network to the prefix file
				f_nets.write(net+"\n")
				# Perform BValue Steps for all addresses of the network and write the to the address/scan file
				#print(net+"|"+",".join(net_addr))
				addr_generated+=bvalue_steps_for_network(f_out,net_addr,bits,nr_addr,stop,network_border)				
			
	# Take the current time and output counts
	end_time = time.time()
	print("Total time needed: " + str(end_time - start_time))
	print("Skipped " + str(network_border_error) + " lines (Invalid Subnet Space)")
	print("Generated a total of: " + str(addr_generated) +" addresses")

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--inputfile", required=True, type=str, help="<filepath> IPv6 Address File to derive BValue Addresses from (one address per line; r)")
	parser.add_argument("-r", "--routedfile", required=True, type=str, help="<filepath> BGP data in csv format of net,<optional: asn> (r)")
	parser.add_argument("-o", "--outputaddr", required=True, type=str, help="<filepath> File to store the output BValue Address (w)")
	parser.add_argument("-p", "--outputprefixes", required=True, type=str, help="<filepath> ")
	parser.add_argument("-b", "--bits", required=False, type=int, default=8, help="<int> Stepwidth in bits for BValue Steps")
	parser.add_argument("-n", "--nr-addr", required=False, type=int, default=5, help="<int> Number of addresses to generate for each BValue Step")
	parser.add_argument("-s", "--stop", required=False, type=int, default=120, help="<int> Maximum BValue Step")
	args = parser.parse_args()	

	iterate_and_generate_bvalues(args.inputfile, args.routedfile, args.outputaddr, args.outputprefixes, args.bits,args.nr_addr,args.stop)


if __name__== "__main__":
	main()
