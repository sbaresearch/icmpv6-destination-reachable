# Takes the first address per routed network and writes it to a file

import SubnetTree as SubnetTree
import sys
import argparse

def fill_tree(tree,file):
	"""
		Read routed networks to SubnetTree
	"""
	with open(file,'r') as F_BGP:
		for line in F_BGP:
			line=line.strip()
			if line.startswith("#"):
				continue
			try:
				tree[line]=line
			except:
				print("Error adding routed network to tree:"+line)
	return tree

def filter(tree,file):
	"""
		Take the first IPv6 address per routed network and store it in a dict
	"""
	filter_dict={}
	err_filter=0

	with open(file,'r') as F_IN:
		for line in F_IN:
			line=line.strip()
			if line.startswith("#"):
				continue
			
			try:
				net=tree[line]
				if net not in filter_dict:
					filter_dict[net]=line
			except:
				print("Error filtering address:"+str(line))
				err_filter+=1
		print("Done - error:"+str(err_filter))
	return filter_dict

def output(filtered,file):
	"""
		Write dict to file
	"""
	with open(file,'w') as F_OUT:
		for key,val in filtered.items():
			F_OUT.write(val+","+key+"\n")

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--inputfile", required=True, type=str, help="<filepath> IPv6 Address File to filter (one address per line; r)")
	parser.add_argument("-r", "--routedfile", required=True, type=str, help="<filepath> BGP data in csv format of net,<optional: asn> (r)")
	parser.add_argument("-o", "--outputfile", required=True, type=str, help="<filepath> File to store the filtered addresses")
	args = parser.parse_args()	


	tree=SubnetTree.SubnetTree()
	tree=fill_tree(tree,args.routedfile)
	
	filtered=filter(tree,args.inputfile)
	output(filtered,args.outputfile)

if __name__ == "__main__":
    # your main function call here
    main()
