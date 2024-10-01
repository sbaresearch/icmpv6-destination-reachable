import pandas as pd
import sys
import shutil

def addRoundTripTime(f_in,f_out):
	"""
		Merges timestamp columns to RTT if column does not already exist
		Return Value: void
	"""
	df=pd.read_csv(f_in)
	if "rtt" not in df.columns:
		df["rtt"]=df["timestamp_str"].astype(float)-(df["sent_timestamp_ts"].astype(str) +"."+df["sent_timestamp_us"].astype(str).str.zfill(6)).astype(float)
		df["rtt"]=df["rtt"]*1000
		df["rtt"]=[int(x) if x > 0 else round(x,2) for x in df['rtt']]
		df.to_csv(f_out,index=False)
		#We do not need the original file anymore.
		if f_in != f_out:
			shutil.move(f_out,f_in)

def main():
	addRoundTripTime(sys.argv[1],sys.argv[2])

main()
