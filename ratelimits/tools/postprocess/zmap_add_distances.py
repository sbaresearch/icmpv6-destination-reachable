import pandas as pd
import sys 
from pathlib import Path
import argparse
import os
from tqdm import tqdm

def listdir_fullpath(d):
	return [os.path.join(d, f) for f in os.listdir(d)]


def add_distances(folder,output_folder,resp_type=False):
	count_empty=0
	count_echo=0
	
	if not os.path.exists(output_folder):
		os.makedirs(output_folder)

	files=listdir_fullpath(folder)
	files=[x for x in files if "single.csv" in x]
	total=len(files)
	
	for i in tqdm(range(total)):
			file=files[i]
			outfile=os.path.join(output_folder, os.path.basename(file))
			target=file.split("/")[-1].split("_")[0]
			df=pd.read_csv(file)

			# Check if responses exist
			if len(df) == 0:
				count_empty+=1
				continue
			
			# If wanted filter only filter for the response type
			if resp_type != False:
				df = df[df["classification"] == args.type] 
			
			
			if df.iloc[0]["nrsent"]=="echoreply":
				count_echo+=1
				df["nrsent"]=1
				df["classification"]="echoreply"

			if "dist_nrsent" not in df.columns:
				df["timestamp_sent"]=(df["sent_timestamp_ts"].astype(str)+"."+df["sent_timestamp_us"].astype(str).str.zfill(6)).astype(float)
				df["dist_nrsent"]=df[["nrsent"]].diff()
				df["dist_rec"]=round(df["timestamp_str"].diff()*1000)
				df["dist_sent"]=round(df[["timestamp_sent"]].diff()*1000)
				col="dist_rec"
				df[col+"_sum"]=df[col].fillna(0).cumsum()
				col="dist_sent"
				df[col+"_sum"]=df[col].fillna(0).cumsum()
				df.index.name="nrrec"				
				df.to_csv(outfile)

	print("Empty  DFs: "+str(count_empty) +" ("+str(round(count_empty/total))+"%)")
	print("Echo  DFs: "+str(count_echo) +" ("+str(round(count_echo/total))+"%)")
	print("Total Targets: "+str(total))
	

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--folder", required=True, type=str, help="Folder with measurement output")
	parser.add_argument("-t", "--type", required=False, default="timxceed", help="Response Type to Fingerprint (default = timxceeded")
	parser.add_argument("-o", "--output-folder", required=True, type=str, help="Folder to store files with processed measurement output")

	args=parser.parse_args()

	add_distances(args.folder,args.output_folder,args.type)

if __name__ == "__main__":
	main()
