import sys
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from empiricaldist import Cdf
import matplotlib.ticker as tkr
import json
from matplotlib.lines import Line2D

translate_types = {
    "unreach_addr_nonfiltered": "AU",
    "unreach_addr":"AU",
    "timxceed": "TX",
    "unreach_noroute": "NR",
    "unreach_admin": "AP",
    "unreach_noport": "PU",
    "unreach_rejectroute": "RR"
}

keys_ordered=["NR","AP","AU","PU","RR","TX"]
colors={"NR":2,"TX":1,"AU":0,"AP":3,"PU":4,"RR":5}

def msfmt(x, pos):
    """ Format milliseconds to seconds for visualization """
    s = '{}'.format(int(x / 1000))
    return s

def get_next_resp_type(response_types,i,x):
	
	wanted=keys_ordered[i]
	
	response_type,group=response_types[x]
	if response_type == wanted:
		#response_type=translate_types[response_type]
		return response_type,group
	else:
		x+=1
		return get_next_resp_type(response_types,i,x)
     
def plot(df,active_status):
    """ Generate CDF plot from the dataframe """
    plt.style.use("bmh")
    my_cmap = list(plt.get_cmap("Dark2").colors)
	#my_cmap = list(plt.get_cmap("tab10").colors)
    linetypes=["solid","dotted","dashed","dashdot"]
    rcParams['font.family'] = 'monospace'
    rcParams['font.size'] = 12
    rcParams['axes.facecolor'] = 'white'
    rcParams['pdf.fonttype'] = 42
    rcParams['ps.fonttype'] = 42
    xfmt = tkr.FuncFormatter(msfmt)   
   
    response_types=list(df.groupby('classification'))
    #print(response_types)
    i=0
    for row in range(2):
        for col in range(3):
            response_type,group=get_next_resp_type(response_types,i,0)
            #print(response_type)
            cdf=Cdf.from_seq(group.rtt)
            plt.step(cdf.qs,cdf.ps,where="post",color=my_cmap[colors[response_type]], linewidth=1.5,label=response_type, linestyle=linetypes[i%4],alpha=0.9,marker=list(Line2D.markers.keys())[i],markevery=0.1,markersize=4)
            i+=1	
 
    ax = plt.gca()
    ax.xaxis.set_major_locator(plt.MaxNLocator(7))
    ax.xaxis.set_major_formatter(xfmt)
	
    plt.xlim([0,22000])
    plt.legend(loc='lower right')
    plt.gca().xaxis.set_major_formatter(xfmt)
    #plt.xlim([0, max(df.rtt) + 500])
    #plt.legend(loc='lower right')
    plt.xlabel("RTT (s)", fontsize=14)
    plt.ylabel("CDF", fontsize=14)
    if active_status==True:
        fileprefix="active"
    else:
         fileprefix="inactive"
    figure = plt.gcf()
    figure.set_size_inches(2.5,2.9)     #2.5, 2.9

    plt.savefig(fileprefix+"_rtt_distribution_reproduced.pdf", bbox_inches='tight', dpi=300)
    plt.show()
    plt.clf()

def process_data(data, active=True):
    """ Process the data to extract RTT and classification based on active or inactive status """
    records = []
    au_count=0
    au_long_count=0
    au_dict={2:0,3:0,18:0}
    for network, targets in data.items():
        for target, changes in targets.items():
            if len(changes) < 2:
                continue  # Skip networks with less than two changes

            # Choose the first or second element based on the 'active' flag
            index = 0 if active else 1
            selected_change = changes[index]
            #print(selected_change)
            if selected_change['type']=="unreach_addr" or selected_change['type']=="unreach_addr_nonfiltered":
                if int(selected_change["rtt"])>1000:
                    au_long_count+=1
                rtt_in_seconds=int(selected_change["rtt"])/1000
                if rtt_in_seconds > 1.5 and rtt_in_seconds <2.5:
                    au_dict[2]+=1
                elif rtt_in_seconds >=2.5 and rtt_in_seconds< 4.0:
                    au_dict[3]+=1
                elif rtt_in_seconds > 16.0:
                    au_dict[18]+=1
                au_count+=1

            try:
                record = {
                    "classification": translate_types[selected_change['type']],
                    "rtt": float(selected_change['rtt'])
                }
                records.append(record)
            except:
                pass
    if active == True:
    	print(au_dict)
    	for key,val in au_dict.items():
        	print(key)
        	print(val/sum(au_dict.values())*100)
    #print(au_count)
    #print(au_long_count)
    return pd.DataFrame(records)

def main(active_status):
    """ Main function to load data, process it and plot RTT distribution """
    with open(sys.argv[1], 'r') as file:
        data = json.load(file)

    df = process_data(data, active=active_status)
    #print(df)
    plot(df,active_status)

if __name__ == "__main__":
    # Determine active status from command line argument or default to True
    active_status = sys.argv[2].lower() == 'active' if len(sys.argv) > 2 else True
    main(active_status)
