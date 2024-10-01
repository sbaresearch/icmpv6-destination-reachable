import pandas as pd
import argparse
import os
from tqdm import tqdm
import json
from scipy.spatial import distance
import copy
import logging 

collected_timelines={}
collected_timelines_list=[]

def compare_range(row_value,range,treshold):
    """
    Compare row value with range
    """
    lower,upper=str(range).split("-")

    if row_value>=int(lower)-treshold and row_value<=int(upper)+treshold:
        return True
    else:
        return False

def compare_value(row_value,fingerprint,treshold):
    """
    Compare row  value with fingerprint value
    """   
    if abs(row_value-fingerprint)<=treshold:
        return True 
    else:
        return False

def match_bs_ri_rs(rowBS,rowRI,rowRS,error_rates,vendor,tag,treshold):
    """
        Match BS,RI and RS
    """
    matches=0
    BS=error_rates[vendor][tag]["BS"]
    RI=error_rates[vendor][tag]["RI"]
    RS=error_rates[vendor][tag]["RS"]

    # BS is either a range "0-1" or an int 1, so check if the value is in the range or if it is equal
     
    rows=[(rowBS,BS),(rowRI,RI),(rowRS,RS)]
    matches_type=["BS","RI","RS"]
    idx=0
    for ratepair in rows:
        rateparameter,fingerprint=ratepair
        logging.debug(str(rateparameter)+","+str(fingerprint)+","+str(treshold))
        if "-" in str(fingerprint):
            if compare_range(rateparameter,fingerprint,treshold):
                matches+=1
        else:
            if compare_value(rateparameter,fingerprint,treshold):
                matches+=1
        logging.debug(matches_type[idx]+","+str(matches))
        idx+=1
    logging.debug("FINGERPRINT: "+vendor+","+str(BS)+","+str(RI)+","+str(RS)+","+str(matches))
    return matches

def match_bs_ri_rs_old(rowBS,rowRI,rowRS,error_rates,vendor,tag):
    """
        Match BS,RI and RS
    """
    matches=0
    BS=error_rates[vendor][tag]["BS"]
    # BS is either a range "0-1" or an int 1, so check if the value is in the range or if it is equal
     
    if "-" in str(BS):
        lower,upper=str(BS).split("-")
        if rowBS<=int(upper):
            matches+=1
            #if compare_range(rowBS,BS):
            #    matches+=1
    else:
        if int(BS) == 6: # Its a Linux, look for an exact match (5,6 or 7)
            if rowBS == int(BS) or rowBS == 5 or rowBS == 7:
                matches+=1
        elif int(BS) == 11: # Cisco / H3C Conflict, be picky
            if rowBS==int(BS):
                matches+=1        
        elif rowBS <= int(BS):
            matches+=1

    # Match The Refill Interval
    RI=error_rates[vendor][tag]["RI"]
    if "-" in str(RI):
        if compare_range(rowRI,RI):
            matches+=1
    elif rowRI == int(RI):
        matches+=1
    
    # Match The Refill Size
    RS=error_rates[vendor][tag]["RS"]
    if "-" in str(RS):
        if compare_range(rowRS,RS):
            matches+=1
    elif rowRS == int(RS):
        matches+=1
    return matches    

def prepare_timeline_with_range(timeline_to_compare,recorded_timeline):
    recorded_timeline=[x for x in recorded_timeline.split(",")]
    # There can be ranges "0-1" or single values "1"
    # If the timeline value is in the range, then set the range to the value else set the range to the either the maximum or the minimum depending on what is closer
    collected_timeline=[]
    for idx,value in enumerate(recorded_timeline):
        if "-" in str(value):
            lower,upper=str(value).split("-")
            #If it is in the range, then set it to the value
            if timeline_to_compare[idx]>=int(lower) and timeline_to_compare[idx]<=int(upper):
                collected_timeline.append(timeline_to_compare[idx])
            else:
                #If it is not in the range, then set it to the value that is closer to the range
                if abs(timeline_to_compare[idx]-int(lower))<abs(timeline_to_compare[idx]-int(upper)):
                    collected_timeline.append(int(lower))
                else:
                    collected_timeline.append(int(upper))
        else:
            collected_timeline.append(int(value))
    return collected_timeline

def match_timeline(timeline,timeline_dict,treshold):
    """
        Match timeline to timeline dict
    """
    distances=[]
    
    #Calculate the distance between the timeline and all the timelines that we learned from the error rates
    for key in timeline_dict.keys():
        # Iterate over lab and snmpv3 timelines
        # The "Timeine" is a string of the form "t1,t2,t3,...,t10", so split it into a list
        if "-" in key:
            #We have to process the range
            collected_timeline=prepare_timeline_with_range(timeline,key)
        else:
            #We are good to go, but we still have to convert the integer string to a list of integers
            if key not in collected_timelines:
                collected_timeline=[int(x) for x in key.split(",")]
                collected_timelines[key]=collected_timeline
            else:
                # Otherwise we already parsed this timeline and we can use the parsed version
                collected_timeline=collected_timelines[key]
       
        # Call euclidean distance on the two timelines                
        match_distance=distance.euclidean(timeline,collected_timeline)
        distances.append(match_distance)
    
    min_distances=[x for x in distances if x<=treshold]
  
    return min_distances,distances


def perform_additional_matches(bs,ri,rs,matches,distances,error_rates,treshold):
    """
        Match BS,RI and RS
    """
    match_dict={}
    match_index=-1 
    # Iterate over the matches and check if BS,RI and RS match
    for idx,dist in enumerate(distances):
        match_count=0
        if dist in matches:
            vendor,tag=collected_timelines_list[idx][1].split(";")
            match_count+=match_bs_ri_rs(bs,ri,rs,error_rates,vendor,tag,treshold)
            logging.debug("SCORE: "+vendor+","+str(bs)+","+str(ri)+","+str(rs)+","+str(match_count))
            match_dict[idx]=match_count
    logging.debug("Match dict: "+str(match_dict)) 
    
    # Now we have the matches, we can check if there are multiple matches
    all_matches=list(match_dict.values())
    max_match=max(all_matches)           
    # Only take matches that match BS,RI and RS
    if max_match<3:
        return -1
    
    if all_matches.count(max_match)>1:
        # If there is more than one match, the one with the least distance wins
        match_index=distances.index(min(matches))
    else:
        # Retrieve idx from match_dict
        for match_index,match_count in match_dict.items():
            if match_count==max_match:
                break

    return match_index
       
       
def calc_treshold(nr10):
    """"
        Calculate treshold based on nrpackets
    """     
    # NR10 can be range, if it is take their lower value
    if "-" in str(nr10):
        nr10=int(nr10.split("-")[0])
    # Set threshold based on NR10, the higher the NR10, the higher the threshold
    if nr10 < 100:
        treshold=10.0
    elif nr10<500:
        treshold=30.0    
    elif nr10<750:
        treshold=60.0
    elif nr10<2000:
        treshold=100.0
    else:
        treshold=500.0
    return treshold

def perform_matches(df,timeline_dict,error_rates):
    """
    Perform matches
    """
    # Use itertuples to iterate over rows
    row_count=0
    for row in tqdm(df.itertuples(), total=df.shape[0]):
        row_count+=1
        match=None

        #Dont match if multiple rate limits are set
        if row.rate_category == "double":
            match = ("0,0,0,0,0,0,0,0,0,0","Double rate limit")
        else:
            #Generate timeline from "t1,t2,t3,...,t10 columns"
            timeline=[]
            for i in range(1,11):
                timeline.append(getattr(row,"t"+str(i)))
                    
            # Calculate treshold based on nrpackets
            treshold=calc_treshold(row.nrpackets)

            # Get all timelines that are within the treshold of the minimum distance
            matches,distances=match_timeline(timeline,timeline_dict,treshold)
            # If we have no matches 
            logging.debug("Matches: "+str(matches))
            if len(matches)==0:
                 match=("-1,-1,-1,-1,-1,-1,-1,-1,-1,-1","New pattern")
            else:
                # If multiple distances match, take the one that matches BS,RI and RS
                if len(matches)>1:
                    bs=row.initial_responses
                    ri=row.refillinterval
                    rs=row.refillsize
                    winner=perform_additional_matches(bs,ri,rs,matches,distances,error_rates,treshold)
                    # No match had a full match of BS,RI and RS
                    if winner==-1:
                        match=("-1,-1,-1,-1,-1,-1,-1,-1,-1,-1","New pattern")
                else:
                    winner=distances.index(min(matches))

                if match == None:
                    # Retrieve the winner
                    for idx,key in enumerate(timeline_dict.keys()):
                        if winner==idx:
                            match=key
                    # Retrieve tag from the match
                    vendor,ratelimit=timeline_dict[match].split(";")
                    # Log Vendor and Ratelimit
                    logging.debug("Vendor: "+vendor+" Ratelimit: "+ratelimit)
                    tag=error_rates[vendor][ratelimit]["TAG"]                
                    winning_timeline=error_rates[vendor][ratelimit]["timelines"][0]
                    match=(winning_timeline,vendor+" "+tag)            
                
            

        # For each row, add the match to the dataframe
        df.at[row.Index,"timeline_match"]=match[1]
        df.at[row.Index,"timeline_match_series"]=match[0]
    
    print("Rows processed: "+str(row_count))
    return df

def add_to_timeline_dict(timeline_dict, error_rates):
    """
    Add json file to timeline dict
    """
    global collected_timelines_list
    
    #Iterate over vendors and add their timelines with the ratelimit number to the timeline dict
    for key in error_rates.keys():
        for ratelimit in error_rates[key].keys():
            for timeline in error_rates[key][ratelimit]["timelines"]:
                value=key+";"+ratelimit
                timeline_dict[timeline]=value
                collected_timelines_list.append((timeline,value))           

    #collected_timelines_list=[(timeline,vendor) for timeline,vendor in timeline_dict.items()]
    return timeline_dict

def filter_error_rates(error_rates, filter):
    filtered_results = {}

    for system, ratelimits in error_rates.items():
        for ratelimit, attributes in ratelimits.items():
            match = True
            for key, value in filter.items():
                if attributes.get(key) != value:
                    match = False
                    break
            if match:
                if system not in filtered_results:
                    filtered_results[system] = {}
                filtered_results[system][ratelimit] = attributes

    return filtered_results


def orchestrate_error_rate_matching(ratefile,collectedfile,outfile,response_type,labrun=False):
    timeline_dict={}
    # timeline1:"Huawei,ratelimit1"
    with open(ratefile) as f:
        error_rates = json.load(f)
        if labrun:
            error_rates = filter_error_rates(error_rates,filter={"TYP":"lab"})        
        add_to_timeline_dict(timeline_dict,error_rates)
    print(timeline_dict)
    
    #### Read the collected data and process it
    df=pd.read_csv(collectedfile)
  
    ### Reduce the df to the resp_type
    df=df[df["resp_type"]==response_type]
  
    #Add match as column to dataframe
    df=perform_matches(df,timeline_dict,error_rates)

    print("Matching complete")
    #Trim the number if the match includes one 
    df["timeline_match_grouped"]=df["timeline_match"].apply(lambda x: str(x).rstrip('0123456789 .').replace("unknown",""))
    print(df["timeline_match_grouped"].value_counts())

    #Dump dataframe to csv
    df.to_csv(outfile,index=False)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--collected", required=False, default="../2_measure_rate_limits/processed_collected.csv", type=str, help="CSV with collected zmap processed data")
    parser.add_argument("-r", "--rates", required=False, default="rates.json", type=str, help="Json with error rates")
    # Debug argument
    parser.add_argument("-d", "--debug", action='store_true', help="Debug")
    parser.add_argument("-t", "--test", action='store_true', help="Testrun")
    parser.add_argument("-code", "--response_code", required=False, default="timxceed", type=str, help="Response type to match")

    parser.add_argument("-l", "--labrun", action='store_true', help="Only match against router fingerprints from the routerlab")
    args=parser.parse_args()

    if args.test:
        args.collected="../2_measure_rate_limits/processed_test.csv"
        outfile="matches_test.csv"
    else:
        if args.labrun:
             outfile="matches_lab.csv"        	
        else:
             outfile="matches.csv"
            
    # Only Log Warnings
    if args.debug:
        logging.basicConfig(level=10)
    else:	
        logging.basicConfig(level=20)
	# Debug Log
    #

    ### 1. Read error rate json with format
    # "Huawei": {
    #	"ratelimit1":{
    #		"TYP":"lab",
    #		"TAG":"NE40",
    #		"NR10":1006-1100,
    #		"timelines":["106-190,100,100,100,100,100,100,100,100,100"],
    #		"BS":106-190,
    #		"RI":1000,
    #		"RS":100
    #	},
    orchestrate_error_rate_matching(args.rates,args.collected,args.outfile,args.response_code,args.labrun)


if __name__ == "__main__":
    main()
