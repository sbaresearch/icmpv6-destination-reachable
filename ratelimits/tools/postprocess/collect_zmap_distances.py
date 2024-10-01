
### Imports
#General
import os
import argparse

#Descriptive Statistics
import pandas as pd
from statistics import median
from statistics import mean
from statistics import stdev
import pyasn

#Progress Bar
from tqdm import tqdm

#Logging
import logging


scanrate=5 #Request every <scanrate> ms
token_treshhold=8 #5ms + 3ms (buffer)= 8ms
duration=10 # 10 seconds of data collection

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def column_to_seconds_ary(column):
	seconds_ary=[0 for i in range(duration)]
	for ms in column:
		second=int(ms/1000)
		if second < duration:
			seconds_ary[second]+=1
	return seconds_ary

def packets_dropped(column):
	"""
		Verify if sent packets are dropped or added to an queue and then processed without package drop (Juniper does sth like this)
	"""
	to_comp=0
	dropped=False
	for sentnr in column:
		if sentnr - 1 != to_comp:
			dropped=True
		to_comp+=1
	return dropped


def parse_centrality_count(targetfile):
	"""
		Hitlist CSV contains the following columns under (/opt/IPv6/Hitlist/router_targets_ttle_only.csv): source_ip,count,destination_ip,first_hop
	"""
	
	centralitydict={}
	df = pd.read_csv(targetfile)
	for idx,row in df.iterrows():
		centralitydict[row["source_ip"]]=row["count"] #+","+row["destination_ip"]
	return centralitydict

def adaptive_round(n):
    #return n based on
    if n < 10:
        return round(n)
    elif n < 500:
        return round(n / 10) * 10
    elif n < 10000:
        return round(n / 100) * 100
    else:
        return round(n / 1000) * 1000

def determine_initial_responses(col_dist_nrsent,col_dist_sent,skipval=1):
	"""
		Distance Sent means that if the bucket is not empty, every request leads to a response, once the bucket is empty dist_nrsent becomes > 1
	"""
	initial_responses=0
	initial_time=0
	for dist in col_dist_nrsent:
		if pd.isnull(dist)== False and dist > skipval: 
			break
		initial_time+=col_dist_sent[initial_responses]
		initial_responses+=1
	return initial_responses,initial_time

def calculate_bucket_size(initial_responses,initial_time,refill_size, refill_interval,scanrate=5):
	#Time based, no packet loss considered: return round(initial_time/scanrate)
	#Considering packet loss and a refill during the initial bucket size depletion
	bucket_size=0
	if initial_time > refill_interval and refill_size>0 and refill_interval>0:
		# We take the minimum of:
		# 1) The time that is after the refill but initial tokens were still returned * our scanrate
		# 2) The number of refills that could have happened * the refill size
		bucket_size=round(initial_responses-min((initial_time-refill_interval)*200/1000,int(initial_time/refill_interval)*refill_size))
	else:
		bucket_size=initial_responses
	return bucket_size

def convert_refill_distances_to_inter_burst_times(distances,original_saddr,col_dist_nrsent):
	"""
		Convert refill distances to inter burst times, for each burst calculate the refill size
	"""
	inter_burst_times=[]
	refill_sizes=[]
	
	# Current Variables	
	inter_burst_time=0
	refill_size=1
	first_refill=True
	
	for request_idx,current_distance in enumerate(distances):
		#If a token in the bucket exists, we add the distance to the inter burst time and increase the refill size by 1
		nrsent_dist=col_dist_nrsent[request_idx]
		if pd.isnull(nrsent_dist)== True:
			continue
		if nrsent_dist == 1:
				inter_burst_time+=current_distance
				refill_size+=1 #int(current_distance/scanrate)
		# If the token in the bucket is depleted, we add the distance to the inter burst times and increase the refill size by 1
		else:
			
			refill_sizes.append(refill_size)
			inter_burst_time+=current_distance
			inter_burst_times.append(inter_burst_time)
	
			# Reset Counters
			refill_size=1
			inter_burst_time=0

	# Refill interval is the median of all inter burst times + an adaptive round to the nearest 10,100,1000
	try:
		if len(inter_burst_times) == 1:
			refill_interval=inter_burst_times[0]
			refill_distance=0
			refill_stdev=0
		else:
			refill_interval=adaptive_round(median(inter_burst_times))
			refill_stdev=round(stdev(inter_burst_times),0)
			refill_distance=max(inter_burst_times)-min(inter_burst_times)
	except:
		refill_interval=0
		refill_stdev=0
		refill_distance=0
		logging.debug("No refill happened : "+original_saddr)
	logging.debug("rate:inter_burst_times:"+",".join(map(str,inter_burst_times)))
	logging.debug("rate:refill_sizes:"+",".join(map(str,refill_sizes)))
	# Refill size is median of all refill sizes
	try:
		refill_size=int(median(refill_sizes))
	except:
		refill_size=0
	
	return refill_interval,refill_size,refill_stdev,refill_distance

def determine_rate_status(refill_distances,scanrate=5):
	# 1. Determine if the rate limit mechanism is regular or not 
	# 1.1 Retrieve distances when no token was in the bucket	
	if len(refill_distances) ==0:
		return -1,0
	refill_distance=median(refill_distances)
	#logging.debug("rate:refill_distances:"+",".join(map(str,refill_distances)))

	# If max(refill_distances)/median(refill_distances) larger than treshhold, we have a single token/bucket rate
	regular_rate=True

	treshhold=0.50	
	logging.debug("rate:score:"+str(mean(refill_distances)/refill_distance))
	skewness=round(abs(1 - mean(refill_distances)/refill_distance),2)
	if  skewness > treshhold:
		regular_rate=False

	logging.debug("rate:score:"+str(max(refill_distances)/refill_distance))
	return regular_rate,skewness

def determine_rate_status_200(refill_distances,scanrate=5):
	if len(refill_distances) ==0:
		return 0	
	values_out_of_range=0
	
	# 1. Determine if the rate limit mechanism is regular or not
	refill_distance=median(refill_distances)
	for value in refill_distances:
		# If a value is 200ms off the median, the rate limit mechanism is not regular
		if abs(value-refill_distance) > 200:
			values_out_of_range+=1
			break
	return values_out_of_range


def determine_rate_parameters(col_dist_nrsent,col_dist_sent,refill_distances,original_saddr):
	"""
		Determine Rate Limit Parameters
		-> Regular Rate Limits
			-> Single Token/Bucket
				-> BS,RI,RS
			-> Generically Rate Limited
				-> BS=RS, RI			
	"""
	# 0. Initialize Variables
	refill_size=refill_interval=initial_time=initial_responses=bucket_size=0

	# 1. Initial responses
	initial_responses,initial_time=determine_initial_responses(col_dist_nrsent,col_dist_sent)
	logging.debug("rate:initial_responses:"+str(initial_responses))
	logging.debug("rate:initial_time:"+str(initial_time))

	# 2. Take the median of the refill distances as the refill distance, determine the refill interval based on that
	# Determine the median refill distance
	refill_interval,refill_size,refill_stdev,refill_distance=convert_refill_distances_to_inter_burst_times(col_dist_sent,original_saddr,col_dist_nrsent)
	logging.debug("rate:refill_interval:"+str(refill_interval))
	logging.debug("rate:refill_size:"+str(refill_size))
	logging.debug("rate:refill_stdev:"+str(refill_stdev))
	logging.debug("rate:refill_distance:"+str(refill_distance))

	# 4. Calculate the bucket size
	bucket_size=calculate_bucket_size(initial_responses,initial_time,refill_size, refill_interval,scanrate)
	
	return refill_interval,refill_stdev,refill_distance,refill_size,initial_responses,initial_time,bucket_size


def retrieve_refill_distances(col_dist_nrsent,col_dist_sent,skipval=1):
	"""
		Retrieve refill distances (distances when no token was in the bucket)
	"""
	refill_distances=[]
	for packet_idx,dist in enumerate(col_dist_nrsent):
		if pd.isnull(dist)== True:
			continue 
	
		if dist > skipval:
			refill_distances.append(col_dist_sent[packet_idx])
	return refill_distances

def reduce_bins(binary,mask):
	"""
		Reduces binary to REDUCTION bins per Second based on Granularity
		Input: [packetsbin1,packetsbin2,packetsbin3,...packetsbinn]
	"""
	red_binary=[]
	i=0
	#print(binary)
	for flag in mask:
		if flag=="1":
			red_binary.append(binary[i])
		i+=1
	#print(red_binary)
	return red_binary

def dist_col_to_granularity(col,granularity=1):
    """
    Takes Column of DataFrame
    Takes Granularity in (s): 0.001 would be ms, 0.1 would be 100ms
    """

    # Create bins based on granularity
    max_time = 10000  # for 10 seconds of data
    bins = list(range(0, max_time+int(granularity * 1e3), int(granularity * 1e3)))
    df_bin = pd.DataFrame({
        'elapsed_time': col,
        'bins': [1]*len(col)
    })

    grouped = df_bin.groupby(pd.cut(df_bin['elapsed_time'], bins, right=False), observed=False).sum()
    #print(grouped)
    binary = list(grouped["bins"].values)

    return binary

def filter_responses(df):
	"""
	Priotize timxceeded responses, if they exist
	"""
	# Get unique values in the 'classification' column
	unique_classifications = df['classification'].unique()

	# Check if there is more than one unique classification
	if len(unique_classifications) > 1:
		# Check if 'timxceeded' exists in the 'classification' column
		if 'timxceeded' in df['classification'].values:
			# Filter for 'timxceeded' if it exists
			df_filtered = df[df['classification'] == 'timxceeded']
		else:
			# If 'timxceeded' does not exist, take the classification with the most responses
			df_filtered = df.groupby('classification').apply(lambda x: x.loc[x.index[0]])
	else:	
		# If only one unique classification exists, take the one with the most responses
		df_filtered = df
	
	return df_filtered

def enrich_file(file,original_saddr,res_dict,totalpackets,centralitydict=None,snmp3dict=None,asndb=None,match=True):
	try:
		df=pd.read_csv(file)
	except:
		logging.error("Could not open file:"+file)
		return res_dict
	original_responses=len(df.index)

	# if the dataframe is empty, return
	if len(df.index) == 0:
		return res_dict
	
	# If there are more than one response types returned, priotize timxceeded
	df = filter_responses(df)
		
	#Take first responsive address as evaluation target
	saddr=df.iloc[0]["saddr"]
	resp_type=df.iloc[0]["classification"]
	#Reduce responses to this address
	if match==True:
		df[df["saddr"] == saddr] 
	reduced_responses=len(df.index)
	if reduced_responses != original_responses:
		logging.info(str(original_responses-reduced_responses)+" responses have been dropped!")
	#Verify if this response came from the original_saddr
	if saddr==original_saddr:
		response_from_target=True
	else:
		response_from_target=False
	if "saddr" in res_dict:
		res_dict["saddr"]=saddr
	if "original_saddr" in res_dict:
		res_dict["original_saddr"]=original_saddr
	if "resp_type" in res_dict:
		res_dict["resp_type"]=resp_type
	if "asn" in res_dict or "network" in res_dict:
		try:
			asn,network=asndb.lookup(saddr)
		except:
			asn=None
			network=None
	if "asn" in res_dict:
		res_dict["asn"]=asn
	if "network" in res_dict:
		res_dict["network"]=network
	if "target_asn" in res_dict or "target_network" in res_dict:
		try:
			target_asn,target_network=asndb.lookup(original_saddr)
		except:
			target_asn=None
			target_network=None
	if "target_asn" in res_dict:
		res_dict["target_asn"]=target_asn
	if "target_network" in res_dict:
		res_dict["target_network"]=target_network
	
	if "saddr_matches_original_target" in res_dict:
		res_dict["saddr_matches_original_target"]=response_from_target

	#Verify if the source ASn matches the targets ASn
	if "asn" in res_dict and "target_asn" and "saddr_matches_original_asn" in res_dict:
		if res_dict["asn"] == res_dict["target_asn"]:
			res_dict["saddr_matches_original_asn"]=True
		else:
			res_dict["saddr_matches_original_asn"]=False

	#Verify if the source matches the targets network
	if "saddr_matches_original_network" in res_dict:	
		if res_dict["network"] == res_dict["target_network"]:
			res_dict["saddr_matches_original_network"]=True
		else:
			res_dict["saddr_matches_original_network"]=False

	if "packets_dropped" in res_dict:
		if "nrsent" in df:
			res_dict["packets_dropped"]=packets_dropped(df["nrsent"])

	if "nrpackets" in res_dict:
		res_dict["nrpackets"]=len(df["dist_sent"])

	if "nrsent" in df:
		if res_dict["nrpackets"] < (totalpackets-200):
			# Fill the initial distance with 0
			df["dist_sent"]=df["dist_sent"].fillna(0)
			if "rate_category" in res_dict:
				# 0.1 Retrieve Refill Distances
				refill_distances=retrieve_refill_distances(df["dist_nrsent"],df["dist_sent"])
				logging.debug("rate:refill_distances:"+",".join(map(str,refill_distances)))
				rate_regular,skewness=determine_rate_status(refill_distances)
				rate_out_of_200ms=determine_rate_status_200(refill_distances)
				res_dict["skewness"]=skewness
				res_dict["refills_out_of_200ms"]=rate_out_of_200ms
			
				if rate_regular==True:
					res_dict["rate_category"]="single"
				elif rate_regular==False:
					res_dict["rate_category"]="double"
				else:
					# No refill has happened
					res_dict["rate_category"]="norefill"
				if "refillinterval" or "bucketsize" or "refillsize" or "initial_responses" in res_dict:
					logging.debug("rate:distances:"+",".join(map(str,df["dist_sent"])))
					res_dict["refillinterval"],res_dict["refillstdev"],res_dict["refilldistance"],res_dict["refillsize"],res_dict["initial_responses"],res_dict["initial_time"],res_dict["bucketsize"]=determine_rate_parameters(df["dist_nrsent"],df["dist_sent"],refill_distances,original_saddr)
		else:
			res_dict["rate_category"]="toohigh"

	if "snmpv3" in res_dict:
		if snmp3dict!=None:
			if saddr in snmp3dict:
				res_dict["snmpv3"]=snmp3dict[saddr]["vendor"]
				res_dict["snmpv3_mactrue"]=snmp3dict[saddr]["mactrue"]
	
	if "centrality_count" in res_dict:
		if centralitydict!=None:
			if saddr in centralitydict:
				res_dict["centrality_count"]=centralitydict[saddr]

	if "t1" in res_dict:
		timeseries_binned=dist_col_to_granularity(df["dist_sent_sum"],1)
		#print(timeseries_binned)				
		for binary_idx in range(len(timeseries_binned)):
			res_dict["t"+str(binary_idx+1)]=timeseries_binned[binary_idx]
	return res_dict

def init_res_dict():
	res_dict={
		"saddr":None, \
		# Additional Information about the router
		"original_saddr": None, \
		"resp_type": None, \
		"asn":None, \
		"network":None, \
		"target_asn":None, \
		"target_network":None, \
		"saddr_matches_original_target":False, \
		"saddr_matches_original_asn":False, \
		"saddr_matches_original_network":False, \
		# Rate Limit Specific Information
		"packets_dropped":False, \
		"rate_category":"single", \
		"skewness":0, \
		"refills_out_of_200ms":0, \
		"nrpackets":0, \
		"initial_responses":0, \
		"initial_time":0, \
	#	"refilled_firstsecond":0, \
		"bucketsize":0, \
		"refillinterval":0, \
		"refillstdev":0, \
		"refilldistance":0, \
		"refillsize":0, \
		"centrality_count":0, \
		"snmpv3":None,
		"snmpv3_mactrue":False
	}
	for i in range(1,11,1):
		res_dict["t"+str(i)]=0
	return res_dict

def parse_snmpv3file(ground_truth_file):
	"""
		Create dict from snmpv3 ground truth file with format: <,ipv6.saddr,enterpriseid1,enterpriseid2,vendor,engineid_enterpriseid
	"""
	snmpv3dict={}
	df = pd.read_csv(ground_truth_file)
	for row in df.itertuples():
		#print(row)
		snmpv3dict[row.src]={"vendor":row.vendor,"mactrue":row.mactrue}
	return snmpv3dict

def iterate_and_collect_files(files,outcsv,inputfile=None,groundtruth=None,asnfile=None,match_src=True,totalpackets=0):

	# Only Log Warnings	
	logging.basicConfig(level=20)
		
	# Retrieve centrality count from the input file
	centralitydict=None
	if inputfile:
		logging.info("Metadata Preparation: Parsing Centrality Scores")
		centralitydict=parse_centrality_count(inputfile)
	
	# Parse SNMPv3 Vendor Labels
	snmpv3dict=None
	# If path was specified and file exsists
	if groundtruth and os.path.isfile(groundtruth):
		logging.info("Metadata Preparation: Parsing SNMPv3 Vendor Labels")
		snmpv3dict=parse_snmpv3file(groundtruth)
	
	asndb=None
	if asnfile:
		logging.info("Metadata Preparation: Parsing ASN DB")
		asndb= pyasn.pyasn(asnfile)

	# Add header to output file
	res_dict=init_res_dict()
	header=",".join(list(res_dict.keys()))
	if outcsv:
		f_out=open(outcsv,'w')
		f_out.write(header+"\n")
	else:
		print(header)

	print("Metadata Preparation: complete")

	#Iterate Result Folder with Zmap Processed Output
	total=len(files)
	for i in tqdm(range(total)):
			file=files[i]
			logging.debug("file:"+file)
			res_dict=init_res_dict()
			original_saddr=file.split("/")[-1].split(".")[0].split("_")[0]
			#Enrich Zmap Output			
			row=enrich_file(file,original_saddr,res_dict,totalpackets,centralitydict,snmpv3dict,asndb,match_src)
			#Write Row to Outputfile
			if outcsv:	
				f_out.write(",".join(list(map(str,row.values())))+"\n")
			else:
				print(",".join(list(map(str,row.values()))))
			


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", required=False, type=str, help="File with zmap distance output")
	parser.add_argument("-p", "--path", required=False, type=str, help="Path to folder with zmap distance output")
	parser.add_argument("-s", "--searchterm",required=False,type=str,default="",help="Only files with search term will be considered")
	parser.add_argument("-o","--outcsv",required=False, type=str, help="Path to outputcsv")
	parser.add_argument("-i","--inputfile",required=False, type=str,help="Inputfile that served as an input for the ZMAP scans (routers with hops and centrality count)")
	parser.add_argument("-g","--groundtruth",required=False, type=str, default="data/data_ratelimits/targets_with_vendor.csv", help="SNMPv3 Ground Truth Data")
	parser.add_argument("-a","--asnfile",required=False,default="data/data_ratelimits/ipasn_20230727.dat",type=str,help="Path to pyasn database")
	parser.add_argument("-m","--match",required=False,action="store_false",help="Do not filter responses from other source addresses")
	parser.add_argument("-t","--totalpackets",required=False,type=int, default=2000,help="Number of packets sent")
	args=parser.parse_args()


	# Enumerate input
	files=[]
	if args.file:
		files.append(args.file)
	elif args.path:
		files=listdir_fullpath(args.path)
		files=[file for file in files if args.searchterm in file and ".pdf" not in file]
	else:
		print("Either file or path is required!")
		exit(1)

	iterate_and_collect_files(files,args.outcsv,args.inputfile,args.groundtruth,args.asnfile,args.match,args.totalpackets)
	


if __name__ == "__main__":
	main()
