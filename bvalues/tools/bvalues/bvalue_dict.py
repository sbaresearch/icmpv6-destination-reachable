import sys
import math
import ipaddress
from bitstring import BitArray
import random
import os
import math
from treelib import Tree,Node
import re
import SubnetTree
import numpy as np
import statistics 
from tqdm import tqdm
import struct
import socket
import argparse
import pprint
import json
import pandas as pd

response_types={"icmpv6":["unreach_noroute", "unreach_admin", "unreach_beyondscope", "unreach_addr","unreach_noport", "unreach_policy", "unreach_rejectroute", "unreach_err_src_route", "unreach", "toobig", "paramprob", "timxceed", "other", "echoreply", "unreach_addr_nonfiltered" ,"empty"], \
"tcp":["unreach_noroute", "unreach_admin", "unreach_beyondscope", "unreach_addr","unreach_noport", "unreach_policy", "unreach_rejectroute", "unreach_err_src_route", "unreach", "toobig", "paramprob", "timxceed", "other", "rst", "synack", "other_tcp_flag", "fragment", "unreach_addr_nonfiltered", "empty"], \
"udp": ["unreach_noroute", "unreach_admin", "unreach_beyondscope", "unreach_addr","unreach_noport", "unreach_policy", "unreach_rejectroute", "unreach_err_src_route", "unreach", "toobig", "paramprob", "timxceed", "other", "udp", "unreach_addr_nonfiltered","empty" ] }

def file_len(fname):
    i=0
    for i, l in enumerate(fname):
            pass
    fname.seek(0)
    return i + 1

def fill_tree(tree, file, suffix=None):
	with open(file, 'r') as fh:
		for line in fh:
			line = line.strip().split(",")[0]
			try:
				tree[line] = line
			except ValueError as e:
				print("Skipped line '" + line + "'", file=sys.stderr)
	return tree

def create_as_dict(as_file):
	as_dict={}
	with open(as_file, 'r') as fh:    	
		for line in fh:
			line = line.strip().split(",")
			prefix=line[0]
			as_nr=line[1]
			try:
				as_dict[prefix] = as_nr
			except ValueError as e:
				print("Skipped line '" + line + "'", file=sys.stderr)
	return as_dict

def column(matrix, i):
    return [row[i] for row in matrix]
    
def read_flipped_addr_results(flip_file,request_protocol):
	"""
		Converts last bit flip results to dict
	"""
	flip_dict={}
	with open(flip_file,'r') as f_flip:
		resp_types=response_types[request_protocol]
		f_flip.readline()
		for line in f_flip:
			#try:
				orig_dest_ip,classificaton,saddr,ttl,original_ttl,sent_timestamp_ts,sent_timestamp_us,timestamp_str,rtt=line.strip().split(",")
				code=int(resp_types.index(classificaton))
				if code==3 and float(rtt)>1000:
					code=int(resp_types.index("unreach_addr_nonfiltered"))
					classificaton="unreach_addr_nonfiltered"
				flip_dict[orig_dest_ip] = str(classificaton)+","+saddr+","+ttl+","+original_ttl+","+rtt
			#except:
			#	print("Error reading last bit flip result: "+line)
	return flip_dict
	
def gen_tree(addr,network_border,bits,stop):
	"""
		Creates BValue Tree from IPv6 Addresses, The network Border and the Number of Bits for a BValue Steps
		The stop Value indicates the IPv6 Prefix Size Where to Stop
	"""
	new_addr=[]
	start=network_border
	for x in range(network_border, stop):
		if (stop-x) % bits == 0:
			start=x
			break

	ip_orig=BitArray(bytes=ipaddress.IPv6Address(addr[0]).packed).bin[:start]
	addr=[bin(int(ipaddress.IPv6Address(ip)))[2:].zfill(128) for ip in addr]

	to_comp=[]
	to_comp_addr=[]

	x=start
	while x < stop-bits:
		addr_part=[h[x:x+bits] for h in addr]
		to_comp.append(addr_part)
		x+=bits	

	addr_tree=Tree()
	addr_tree.create_node(ip_orig,ip_orig)
	for i in range(len(to_comp[0])):
		col=column(to_comp,i)
		oldEl=ip_orig
		path=ip_orig
	
		for el in col:
			path+="/"+el
			if not addr_tree.get_node(path):
				addr_tree.create_node(el,path,parent=oldEl)
			oldEl=path

	return addr_tree

def most_frequent(List): 
    return max(set(List), key = List.count) 

def int_from_ipv6(addr):
   addr=addr.split("/")[0]
   hi, lo = struct.unpack('!QQ', socket.inet_pton(socket.AF_INET6, addr))
   return (hi << 64) | lo

def check_diff(addr1,addr2):
   addr1=int_from_ipv6(addr1)
   addr2=int_from_ipv6(addr2)
   
   diff=addr1 ^ addr2
   
   try:
      #out=BitArray(int=diff).bin.index("1")
      out=f"{diff:b}".zfill(128)   
      out=out.index("1")+1
   except:
      out=128
   return out  
   
def flip(binary_str):    
    return ''.join('0' if i == '1' else '1' for i in binary_str)


def tree_to_addr_list(tree):
	addr_unsorted=[]
	for node in  tree.expand_tree():
		addr_unsorted.append(tree[node].identifier.replace("/",""))
	#Sort BValue Addresses 
	addr_sorted=sorted(addr_unsorted, key=len)

	return addr_sorted

def match_response_dict(f_targets,addr_sorted,scanned,nr_packets):
	#For each generated addr to fingerprint collect the scan results
	response_dict={}
	for addr in addr_sorted:
		# We sent x nr packets for one addr
		response_dict[addr]={}
		for i in range(nr_packets):
			try:
				#We read the random bvalue addr that was logged in the input file for the scan
				target=f_targets.readline().rstrip()
				resp_type,outersaddr,ttl, orig_ttl, rtt=scanned[target].split(",")
				same_bits=str(check_diff(target,outersaddr))
			except:
				#No response was received
				resp_type="empty"
				same_bits,outersaddr,ttl,orig_ttl,rtt="-1","empty","-1","-1","-1"
			
			#Add to results dict
			if resp_type not in response_dict[addr]:
				response_dict[addr][resp_type]={"count":1,"same_bits":[same_bits],"srces":[outersaddr],"rtt":[rtt],"ttl":[ttl],"ttl_at_target":[orig_ttl]}
			else:
				#Add resutls
				response_dict[addr][resp_type]["count"]+=1
				response_dict[addr][resp_type]["rtt"].append(rtt)
				response_dict[addr][resp_type]["ttl"].append(ttl)
				response_dict[addr][resp_type]["ttl_at_target"].append(orig_ttl)
				if outersaddr not in response_dict[addr][resp_type]["srces"]:
					response_dict[addr][resp_type]["srces"].append(outersaddr)

		for resp_type in response_dict[addr]:
			response_dict[addr][resp_type]["rtt"]=np.mean(list(map(float,response_dict[addr][resp_type]["rtt"])))
			response_dict[addr][resp_type]["ttl"]=np.mean(list(map(int,response_dict[addr][resp_type]["ttl"])))
			response_dict[addr][resp_type]["ttl_at_target"]=np.mean(list(map(int,response_dict[addr][resp_type]["ttl_at_target"])))
	
	return response_dict

def match_highest_bvalue_with_net_addr(net_addr,bvalue_addr):
	same_bits=[]
	addr2=str(ipaddress.IPv6Address(BitArray(bin=bvalue_addr+"0"*(128-len(bvalue_addr))).tobytes()))
	for idx,addr1 in enumerate(net_addr): 
		same_bits.append(check_diff(addr1,addr2))
	return net_addr[same_bits.index(max(same_bits))]

def add_bvalue_results(bvalue_dict,  f_targets, flip_dict, responsiveness_dict, scanned, net, net_addr, bits, stop, nr_packets, network_border, request_protocol):
	"""
		Generate BValue Dict for each Address of an IPV6 Network
	"""	
	resp_types=response_types[request_protocol]
	
	#Get Nr of different Response Types and Codes
	len_resp_types=len(resp_types)

	#Recreate Bvalue Tree from Target Addresses and get BValue Target Addresses
	tree=gen_tree(net_addr,network_border,bits,stop)	
	
	#Generate addr list from tree
	addr_sorted=tree_to_addr_list(tree)

	#Match scan data to bvalue addresses
	response_dict=match_response_dict(f_targets,addr_sorted,scanned,nr_packets)




	for leaf in tree.paths_to_leaves():
		target=match_highest_bvalue_with_net_addr(net_addr,leaf[-1].replace("/",""))
		#print(target)
		for path in leaf:
			#Each tree level is separated by "/", remove them as we dont need them
			bval_addr=path.replace("/","")
			#Get current bvalue (length of fixed bytes in bvalue address)
			bval="B"+str(len(bval_addr))
			bval_results=response_dict[bval_addr]
			bvalue_dict[net]["targets"][target]["bvalues"][bval]={}
			bvalue_dict[net]["targets"][target]["bvalues"][bval]=bval_results

		if net_addr[0] in responsiveness_dict:
			responsive=1
		else:
			responsive=-1
		bvalue_dict[net]["targets"][target]["hitlist_responsive"]=responsive


		if len(flip_dict)>0:
			last_bval_result={}

			#Add responsiveness check to dict 			
			bvalue_dict[net]["targets"][target]["bvalues"]["B127"]={}
			#Assign default values
			classification="empty"
			last_bval_result={"hitlist_responsive":responsive,"count":1,"srces":["empty"],"same_bits":[-1],"rtt":-1,"ttl":-1,"ttl_at_target":-1}
			
			#print(net_addr[0])
			ip_flipped=BitArray(bytes=ipaddress.IPv6Address(net_addr[0]).packed).bin
			last_bit=flip(str(ip_flipped[127]))
			original_ip = BitArray(bin=ip_flipped[:-1]+last_bit)
			original_ip = str(ipaddress.IPv6Address(int(original_ip.bin,2)))
			#print(original_ip)
		
			if original_ip in flip_dict:
				#Verify if non flipped address was responsive to either icmpv6,tcp443 or udp53				
				classification,outersaddr,ttl, orig_ttl, duration=flip_dict[original_ip].split(",")
				same_bits=str(check_diff(original_ip,outersaddr))
				last_bval_result={"count":1,"srces":[outersaddr],"same_bits":[same_bits],"rtt":duration,"ttl":ttl,"ttl_at_target":orig_ttl}
			
			bvalue_dict[net]["targets"][target]["bvalues"]["B127"][classification]=last_bval_result

	return bvalue_dict


def read_scandata(scan_file):
	scanned = {}	
	# Parsing Scan Results
	with open(scan_file,'r') as f_scan:
		for line in f_scan:
			try:
				saddr, resp_type, outersaddr,ttl, orig_ttl, unused_sent_s, unused_sent_ms, unused_rec_timestamp, rtt = line.strip().split(',')
				if resp_type=="unreach_addr" and float(rtt)>1000:
					resp_type="unreach_addr_nonfiltered"
				scanned[saddr] = resp_type+","+outersaddr+","+ttl+","+orig_ttl+","+rtt
			except:
				print("Error reading result: "+ line)
	return scanned
			
def create_bvalue_dict(scan_file,  target_file, hitlist_file, flip_dict, responsiveness_dict, tree, as_dict, bits, stop, request_protocol,nr_packets):
	"""
		Defines Response Types, Parses Scan Results
	
	"""
	f_targets=open(target_file,'r')
	resp_types=response_types[request_protocol]
	
	scanned=read_scandata(scan_file)
	
	# For every address of a network (longest prefix match) get the results for the generated BValue Step Addresses!
	# ! Addresses in f_hitlist have to be sorted
	oldKey = None
	net_addr=[]
	bvalue_dict={}

	skipped_small_prefixes=0
	with open(hitlist_file,'r') as f_hitlist:
		for i, line in enumerate(tqdm(f_hitlist)):
				addr,net,as_nr=line.rstrip("\n").split(",")
				thisKey=net		
				
				#Skip Networks with small prefix sizes (use same stop and bits as during bvalue target generation)
				network_border=int(net.split("/")[1])
				if network_border >= stop-bits:
					skipped_small_prefixes+=1
					continue
	
				net_addr.append(addr)
	
				if oldKey != thisKey:
						#Add basic info to bvalue dict
						bvalue_dict[net]={}
						bvalue_dict[net]["as"]=as_nr
						bvalue_dict[net]["targets"]={}
						for addr in net_addr:
							bvalue_dict[net]["targets"][addr]={"bvalues":{}}
	
						bvalue_dict=add_bvalue_results(bvalue_dict,  f_targets, flip_dict, responsiveness_dict, scanned, net, net_addr, bits, stop, nr_packets, network_border, request_protocol)
						net_addr=[]
	
				oldKey=thisKey
	
	print("Skipped small prefixes >=120:"+str(skipped_small_prefixes))

	return bvalue_dict

def extract_responsiveness_dict(hitlistfile,file):
	"""
		Generate responsiveness dict from Lastbit Measurement results
	"""

	#Evaluate Subnet Activeness Again (we verify hitlist responsiveness)
	#https://ipv6hitlist.github.io/
	# ICMPv6 Echo Request
	# TCP 80/443
	# UDP 53/443
	positive_responses={"echoreply":0,"synack":0,"udp":0}

	#Step 1: Generate responsiveness dict for ICMPV6 Echo Request, TCP 443 and UDP 53
	types=["icmpv6","tcp","udp"]
	
	#Skim through last bit files and add them to the files to evaluate 
	files=[]
	for proto in types:
		if proto in file:
			files.append(file)
		else:
			for proto2 in types:
				proto_file=file.replace(proto2,proto)
				if proto in proto_file:
					files.append(proto_file)
					break

	responsiveness_dict={}
	for idx,file in enumerate(files):
		df_res=pd.read_csv(file)
		for unused,row in df_res.iterrows():
			
			#Extract the original destination
			destip=row["orig-dest-ip"]
			#TCP Module uses '#' for orig-dest-ip if the response is assumed to be coming from the target host and udp uses ''
			if row["classification"] in positive_responses:
				if row["classification"]=="synack" or row["classification"]=="udp": #row["classification"]=="rst" 
					destip=row["saddr"]
			
				if destip not in responsiveness_dict:
					responsiveness_dict[destip]={}
					for typ in types:
						responsiveness_dict[destip][typ]="empty"
					responsiveness_dict[destip][types[idx]]=row["classification"]
				else:
					responsiveness_dict[destip][types[idx]]=row["classification"]

	outdict={}
	hitlist_count=0
	with open(hitlistfile,'r') as f_hitlist:
		for line in f_hitlist:
			line=line.strip().split(",")[0]
			
			if line in responsiveness_dict:
				outdict[line]=1
			hitlist_count+=1

	print("Total Hitlist Addresses:"+str(hitlist_count))
	print("Responsive Hitlist Addresses (ICMPv6/TCP443/UDP53):"+str(len(outdict)))

	
	return outdict

def main():
	"""
		Creates BValue Dict, Adds Additional Data to Scan Data
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--scan-file",required=True,type=str,help="Filename with Output of BValue Scan  (possibly under /scans)")
	parser.add_argument("-n", "--net-file",required=True, type=str,help="Filename with Networks that were used to create BValue Step Addresses")
	parser.add_argument("-t", "--target-file", required=True, type=str, help="Filename with with the BValue Target Addresses for the Scan") 
	parser.add_argument("-i", "--hitlist-file", required=True, type=str, help="Filename with the hitlist used for the Scan!")
	parser.add_argument("-o", "--output-file", required=True, type=str, help="Filename for outputing BValue Matrix")
	parser.add_argument("-f", "--flip-file", required=False, type=str, help="Filename with the results of the last bit flip measurement!")
	parser.add_argument("-a", "--asdata-file", required=True, type=str, help="Filename with AS Data of format net,as_nr")
	parser.add_argument("-b", "--bval-stepwidth", required=False, type=int, default=8, help="Nr of Bits for step width of Bvalue Steps (Default 8)")
	parser.add_argument("-r", "--nr-packets", required=False, type=int, default=5, help="Nr of packets sent for each Bvalue Step")
	parser.add_argument("-m", "--max-bval", required=False, type=int, default=128, help="Maximum BValue Step (Default /128=B120)")
	parser.add_argument("-p", "--protocol", required=False, type=str, default="icmpv6", help="Request Protocol used for the scan!")
	args = parser.parse_args()	
	#Open files

	
	flip_dict={}
	if args.flip_file:
		responsiveness_dict=extract_responsiveness_dict(args.hitlist_file,args.flip_file)
		flip_dict=read_flipped_addr_results(args.flip_file,args.protocol)
	
	tree = SubnetTree.SubnetTree()
	tree = fill_tree(tree,args.net_file)
	
	print("Reading AS Data")
	as_dict=create_as_dict(args.asdata_file)
	
	print("Starting To Create BValue Dict")
	bvalue_dict=create_bvalue_dict(args.scan_file,  args.target_file, args.hitlist_file, flip_dict, responsiveness_dict, tree ,as_dict, args.bval_stepwidth, args.max_bval, args.protocol,args.nr_packets)
	
	with open(args.output_file,'w') as f_out:
		json.dump(bvalue_dict,f_out)
		print("Finished: BValue Dict created successfully!")


if __name__== "__main__":
	main()
