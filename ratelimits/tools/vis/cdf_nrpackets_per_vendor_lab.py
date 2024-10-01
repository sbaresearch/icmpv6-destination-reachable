import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy
from empiricaldist import Cdf
from matplotlib import rcParams
import string
import seaborn as sns
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


def plot_cdf_snmpv3(df,vendor_dict,outfile):
    # Group by vendor and compute CDF for each group
    grouped = df.groupby('snmpv3')['nrpackets']
    
    plt.figure(figsize=(10, 3))
    
    colors = list(plt.get_cmap("tab10").colors)
    #colors = plt.cm.rainbow(np.linspace(0, 1, len(grouped)))
    linestyles = ['-', '--', '-.', ':']
    
    
    idx=0
    
    lab={"huawei":[{"start":1000,"end":1100}], "cisco":[{"start":19,"end":20},{"start":105,"end":106}], "juniper":[{"start":520,"end":521}],"linux kernel":[{"start":15,"end":16},{"start":165,"end":168}],"mikrotik":"linux kernel"} # Keep readability {"start":25,"end":26},{"start":45,"end":46},{"start":85,"end":87} # "hpe":[{"start":2000,"end":2000}
    
    for sorted_name in vendor_dict.keys():
        for (name, group) in grouped:
            if vendor_dict[name] > 1:
                if name == sorted_name and name in lab:
                    x,y=compute_cdf(group)
                    if name in lab:
                        first=True
                        if isinstance(lab[name],list):
                            records=lab[name]
                            record_name=name
                        else:
                            records=lab[lab[name]]
                            record_name=lab[name]
                        for record in records:
                            if record["start"]!=0:
                               if record["start"]-record["end"]==0:
                                   if first==True:
                                        plt.axvspan(record["start"],record["end"],color=colors[idx%len(colors)],label=record_name.title()+ " Lab",alpha=0.6)            
                                        first=False
                                   else:
                                        plt.axvspan(record["start"],record["end"],color=colors[idx%len(colors)],alpha=0.6)
                               else:
                                   if first==True:
                                        plt.axvspan(record["start"],record["end"],color=colors[idx%len(colors)],label=record_name.title()+ " Lab",alpha=0.5)
                                        first=False
                                   else:
                                        plt.axvspan(record["start"],record["end"],color=colors[idx%len(colors)],alpha=0.5)
    
                               
                        plt.step(x, y,where='post', label=name.title()+" SNMPv3: "+f'{vendor_dict[name]:,}', color=colors[idx%len(colors)], linestyle=linestyles[idx%len(linestyles)] , markevery=(0.1,0.1),marker='o', markersize=4)
                        idx+=1
    	
    
    plt.axvspan(1980,2300,color="grey",label="> Scanrate",alpha=.6)
    
    ax=plt.gca()
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    # convert y-axis to Logarithmic scale
    plt.xscale("log")
    # Put a legend to the right of the current axis
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    plt.xlabel("Number of Error Messages")
    plt.ylabel("CDF")
    #plt.legend()
    #plt.grid(True)
    #plt.show()
    plt.savefig(outfile, bbox_inches='tight', dpi=300)


def preprocess_and_plot_snmpv3(collectedfile,outfile):
    df=pd.read_csv(collectedfile)
    df=df.loc[df["resp_type"] == "timxceed"]
    df=df.loc[df["snmpv3"] != None]
    df=df.loc[df["snmpv3"] != "unknown"]
    
    df.loc[df['nrpackets'] > 2000, 'nrpackets'] = 2000
    vendor_dict=df["snmpv3"].value_counts().to_dict()
    
    # Get relevant columns
    df = df[["nrpackets","snmpv3"]]
    plot_cdf_snmpv3(df,vendor_dict,outfile)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--collected", required=False, default="processed_collected.csv", type=str, help="CSV with collected zmap processed data")
    parser.add_argument("-o", "--outfile", required=False, default="cdf_snmpv3.pdf", type=str, help="Output PNG/PDF with CDF")
    args=parser.parse_args()

    preprocess_and_plot_snmpv3(args.collected,args.outfile)

if __name__ == "__main__":
    main()
