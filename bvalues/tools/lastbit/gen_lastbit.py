#python3 gen.py <input-file> <output-file>
# input_format: <IPv6Addr>\n<IPv6Addr>
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
        	if "#" in l:
        		i-=1
    return i + 1

def flip(binary_str):    
    return ''.join('0' if i == '1' else '1' for i in binary_str)

def generate_addr(addr):
	"""
		Generate Bit Flip Address
	"""
	ip_orig=BitArray(bytes=ipaddress.IPv6Address(addr).packed).bin
	last_bit=flip(str(ip_orig[127]))
	new = BitArray(bin=ip_orig[:-1]+last_bit)
	ip = ipaddress.IPv6Address(int(new.bin,2))	
	return ip


def addr_dict(inputfile):
	"""
		Generate Addr lookup dict, in order to avoid hitlist entries where both addr and flipped address are already in the data
	"""
	addr_dict={}
	with open(inputfile,'r') as f_in:
		for line in f_in:
			line=line.strip()
			addr=line.split(",")[0]
			addr_dict[addr]=addr
	return addr_dict

def flip_and_write_to_output (inputfile,outputfile,addr_lookup):
	"""
		Write flipped addr to outputfile
	"""
	print("Generating Addresses")
	in_len=file_len(inputfile)
	f_in = open(inputfile, 'r+')
	f_out= open(outputfile, 'w')
	addr_count=0
	flip_error=0
	for addr in tqdm(f_in, total=in_len):
			if addr.startswith("#"):
				continue
			addr=addr.strip().split(",")[0]
			new_addr=str(generate_addr(addr))

			if new_addr not in addr_lookup:
				f_out.write(addr+"\n")
				f_out.write(str(new_addr)+"\n")
				addr_count+=1
			else:
				flip_error+=1
			
	print("Finished - "+str(addr_count)+" addresses were generated!")
	print("Flip errors avoided: "+str(flip_error))
	f_in.close()
	f_out.close()

def main():
	"""
		Input: List of addresses, Output: Last Bit Flipped Addresses for each Address
	"""
	inputfile = sys.argv[1]
	outputfile = sys.argv[2]

	addr_lookup=addr_dict(inputfile)
	flip_and_write_to_output(inputfile,outputfile,addr_lookup)

if __name__== "__main__":
	main()
