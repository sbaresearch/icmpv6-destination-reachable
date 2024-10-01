import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy
from empiricaldist import Cdf
from matplotlib import rcParams
import argparse

plt.style.use("bmh")
rcParams['font.family'] = 'monospace'
rcParams['axes.facecolor'] = 'white'
rcParams['font.size']= 12
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42


# Function to compute the CDF for a series
def compute_cdf(series):
    #series_sorted = np.sort(series)
    cdf=Cdf.from_seq(series)
    #cdf = np.cumsum(series_sorted) #/ np.sum(series_sorted)
    return cdf.qs, cdf.ps

def draw_cdf(df,centrality_dict,outfile):
    
    # Group by vendor and compute CDF for each group
    grouped = df.groupby('centrality_classification')['nrpackets']
    
    plt.figure(figsize=(6, 4.5))
    
    colors = my_cmap = list(plt.get_cmap("Dark2").colors)[:3][::-1]#list(plt.get_cmap("tab10").colors)
    #colors = plt.cm.rainbow(np.linspace(0, 1, len(grouped)))
    linestyles = ['-', '--', '-.', ':']
    
    
    idx=0
    non_wanted=[]
    for sorted_name in centrality_dict.keys():
        for (name, group) in grouped:
            if name == sorted_name and name not in non_wanted:
                x,y=compute_cdf(group)
                print(name)
            #x=  np.sort(group)
            #y = scipy.stats.norm.cdf(x)
            #print(name+","+str(len(x)))
            #if name=="hpe":
             #   print(group)
            #print(y)
            #x = np.sort(group)
            
                plt.step(x, y, label=f'{centrality_dict[name]:,}'+" "+name, color=colors[idx%len(colors)], linestyle=linestyles[idx%len(linestyles)] , markevery=(0.1,0.1),marker='o', markersize=4)
                idx+=2
    x,y=compute_cdf(df["nrpackets"])
    plt.step(x, y, where='post',label=f'{len(df["nrpackets"]):,}'+" Total", color=colors[1]),# linestyle=linestyles[idx%len(linestyles)])# ,# markevery=(0.1,0.1),marker='o', markersize=4)
         
    plt.axvspan(100, 110, color='red', alpha=0.5,label="RFC4443 Small/Medium Routers", lw=0)
    
    
    #plt.title("CDF of Number of Packets by Vendor")
    #ax=plt.gca()
    #ax.spines['top'].set_visible(False)
    #ax.spines['right'].set_visible(False)
    #plt.xlim(0,2000)
    plt.xlabel("Number of Error Messages")
    plt.ylabel("CDF")
    plt.legend()
    plt.grid(True)
    #plt.show()
    plt.savefig(outfile, bbox_inches='tight', dpi=300)



def preprocess_and_plot_nrpackets(processedfile,outfile):
     # Read CSV
    df=pd.read_csv(processedfile)
	
    df=df.loc[df["resp_type"] == "timxceed"]
    #Filter DF    
    df = df.loc[df['saddr_matches_original_target'] == True]
    
    centrality_classification=[]
    for idx,row in df.iterrows():
        if row["centrality_count"]>1:
            centrality_classification.append("Centrality > 1")
        else:
            centrality_classification.append("Centrality = 1")
    
    # Get relevant columns
    df.loc[df['nrpackets'] > 2000, 'nrpackets'] = 2000
    df["centrality_classification"]=centrality_classification
        
    centrality_dict=df["centrality_classification"].value_counts().to_dict()
    
    df = df[["nrpackets","centrality_classification"]]
    
    draw_cdf(df,centrality_dict,outfile)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--processedfile", required=False, default="../../m2_ratelimits_snmpv3/3_matchtxrates_with_labels/matches.csv", type=str, help="CSV with processed Zmap Distances and Lab Matches")    
    parser.add_argument("-o", "--outfile", required=False, default="nrpackets_centrality_steps.pdf", type=str, help="Path to outputfile (.png,.pdf)")    
    args=parser.parse_args()
 
   
    preprocess_and_plot_nrpackets(args.processedfile,args.outfile)

    
if __name__ == "__main__":
    main()
