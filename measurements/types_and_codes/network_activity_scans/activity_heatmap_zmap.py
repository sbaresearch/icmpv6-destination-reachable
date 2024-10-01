import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import json
from bitstring import BitArray
import ipaddress
import time
import struct
import socket
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker
from scipy.sparse import lil_matrix
import copy

from pathlib import Path
import dask.dataframe as dd
from tqdm import tqdm
# Draw an activity heatpmap of responses, without performing Discriminating Prefix Length (DPL)
# DPL on => network 1, src 1, subnet 1, subnet n => subnet 1n/(same bits prefix)
# DPL off => every target represents a /64

zmap_type_code_to_zmap_classification= {
    "1_0":"unreach_noroute",
    "1_1":"unreach_admin",
    "1_2":"unreach_scope",
    "1_3":"unreach_addr_timeout",
    "1_3_se1sec":"unreach_addr",
    "1_4":"unreach_noport",
    "1_5":"unreach_policy",
    "1_6":"unreach_rejectroute",
    "3_0":"timxceed",
    "129_0":"echoreply"
}

classification_errortypes={
                    "unreach_addr_timeout":"active",
                    "unreach_noport":"ambiguous",
                    "echoreply":"ambiguous",
                    "unreach_noroute":"ambiguous",
                    "unreach_admin":"ambiguous",
                    "unreach_policy":"ambiguous",
                    "unreach_addr":"inactive",
                    "unreach_rejectroute":"inactive",
                    "timxceed":"inactive"
}

classification_int ={
    "nonrouted":0,
    "unresponsive":1,
    "active":2,
    "inactive":3,
    "ambiguous":4
}

classification_table_dict = {
                    "unreach_addr_timeout":"AU>1sec",
                    "unreach_noport":"PU",
                    "echoreply":"ER",
                    "unreach_noroute":"NR",
                    "unreach_admin":"AP",
                    "unreach_policy":"FP",
                    "unreach_addr":"AU",
                    "unreach_rejectroute":"RR",
                    "timxceed":"TX",
                    "echoreply":"ER"
}


def int_from_ipv6(addr):
   addr=addr.split("/")[0]
   hi, lo = struct.unpack('!QQ', socket.inet_pton(socket.AF_INET6, addr))
   return (hi << 64) | lo

def read_networks(file_path,sort=True):
    """Read input networks from json file"""
    with open(file_path, 'r') as file:
        data = json.load(file)    
  
    networks = {}

    # Read networks and their sortval
    for network in data.keys():
        networks[network]={"sortval":int_from_ipv6(network.split("/")[0])}

    if sort:
        # Sort the networks dictionary by 'sortval'.
        sorted_networks = {k: v for k, v in sorted(networks.items(), key=lambda item: item[1]['sortval'])}
        return sorted_networks
    
    return networks


def process_zmap_file(zmapout,f_log,heatmap_matrix):
    zmapout=str(zmapout)

    # If header line is in file take it, otherwise try to assign our header
    with open(zmapout,'r') as f_in:
        header=f_in.readline().strip().split(",")
        if header[0] == "orig-dest-ip":
            dask_df = dd.read_csv(zmapout,sep=',',header=0,names=["orig_dest_ip","classification","saddr","ttl","original_ttl","sent_timestamp_ts","sent_timestamp_us","timestamp_str"])
        else:
            dask_df = dd.read_csv(zmapout,sep=',',header=0,names=["orig_dest_ip","classification","saddr","ttl","original_ttl","sent_timestamp_ts","sent_timestamp_us","timestamp_str"])

        zmap_df = dask_df.compute()


    # Iterate over rows
    rowid=0
    failed=0
    for row in tqdm(zmap_df.itertuples()):
        #Check if row is valid
        if len(row.orig_dest_ip) == 0:
            continue
        
        # Lookup heatmap_matrix_row and column
        # row depends on bits 0 to 32
        # column depends on bits 32 to 64
        try:
            classification=row.classification
            rtt=float(row.timestamp_str)-float(str(row.sent_timestamp_ts)+"."+str(row.sent_timestamp_us).zfill(6))
            rtt=rtt*1000    
            if classification == "unreach_addr":
                #print(row["rtt"])
                if rtt > 1000:
                    classification="unreach_addr_timeout"
            classification_integer=classification_int[classification_errortypes[classification]]

            ipv6int=int_from_ipv6(row.orig_dest_ip)
            # Transform int to bitstring 00111
            addressbits=format(ipv6int, 'b').zfill(128)
            heatrow=row_index_dict[int(addressbits[0:48],2)]
            col=int(addressbits[48:64],2)
            heatmap_matrix[heatrow["rownr"]][col]=classification_integer
        except Exception as e:
            f_log.write(str(rowid)+","+row.orig_dest_ip+"\n")
            failed+=1
        rowid+=1
    print("Finished: "+str(failed))
    f_log.write(classification+","+str(rowid)+"total entries,"+str(failed)+" failed lookup"+"\n")
    return heatmap_matrix


def fill_heatmap_matrix_with_actual_responses(networks,measurementfolder,heatmap_matrix):     
    f_log=open("log_without_dpl_zmap.log",'w')
    for file in Path(measurementfolder).iterdir():       
        heatmap_matrix=process_zmap_file(file,f_log,heatmap_matrix)    
    return heatmap_matrix
# Define a simple function to format ticks as hexadecimal
def format_hex(x, pos):
    return f'0x{int(x):X}'.ljust(6, '0')

# Define a custom formatter function to convert tick labels into the desired format
def format_func(value, tick_number):
    # Value is the tick position; here, we convert it to an integer and then to the desired string format
    return f'{int(value/1000)}K'

row_index_dict={}
def create_heatmap_matrix(networks):   
    ##ln(subnets)#100#len(subnets)
    max_subnets = 2**16 
    # For each network that is larger than /32 split it into multiple /32
    max_rows=0
    for network in networks:
        network,prefix=network.split("/")
        prefix_size=int(prefix)
        netint=int_from_ipv6(network)
        addressbits=format(netint, 'b').zfill(128)
        row_index=int(addressbits[0:48],2)
        row_index_dict[row_index]={"rownr":max_rows,"prefix_size":prefix_size}
        max_rows+=1

    print("Total number of networks ")
    print(max_rows)
    
    heatmap_matrix = np.ones((max_rows,max_subnets)) 

    return heatmap_matrix

def generate_heatmap_zmap(networks,measurementfolder,outputfile):
    """Generate a heatmap based on networks and their subnet classifications."""
    classification_colors = {
     #   'nonrouted' : 0,
        'unknown':1,
        'active': 2,  # Green
        'inactive': 3,  # Red
        'ambiguous': 4  # Yellow
    }
    viridis = plt.cm.get_cmap('viridis', 256)
    plot_colors = {
        'active':  viridis(0.7), 
        'inactive': viridis(0.33),
        'ambiguous':viridis(0.95),
        'unknown':  viridis(0.00)
    }

    cmap= [plot_colors['unknown'], plot_colors['active'], plot_colors['inactive'], plot_colors['ambiguous']] 

    heatmap_matrix=create_heatmap_matrix(networks)
    
    heatmap_matrix=fill_heatmap_matrix_with_actual_responses(networks,measurementfolder,heatmap_matrix)

    cmap=ListedColormap(cmap)
   
    # Plotting the heatmap
    fig, ax = plt.subplots(figsize=(6, 4))
    print("Plotting")
    #ax.pcolormesh(heatmap_matrix, cmap=cmap, rasterized=True)
    c = ax.imshow(heatmap_matrix, cmap=cmap, aspect='auto', origin='lower',interpolation='none')
    print("Plotted")

    # Define the legend handles using patches
    legend_handles = [
        Patch(facecolor=plot_colors['active'], label='Active'),
        Patch(facecolor=plot_colors['ambiguous'], label='Ambiguous'),
        Patch(facecolor=plot_colors['inactive'], label='Inactive'),
        Patch(facecolor=plot_colors['unknown'], label='Unresponsive'),
    ]

    # Create a legend on the plot
    print("Plotting legend")
    ax.legend(loc="upper right",handles=legend_handles, title='Classification')

    ax.set_ylabel('# of Networks')

    ticks = [0x2000 * i for i in range(9)]  # Generates 0x0000, 0x2000, ... up to 0x10000
    ticks[-1]-=1
    ax.set_xticks(ticks)   
    ax.xaxis.set_major_formatter(FuncFormatter(format_hex))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))   
    
    ax.tick_params(axis='x', labelrotation=45)
    for label in ax.get_xticklabels():
        label.set_ha("right")  # Set horizontal alignment to right
        label.set_rotation_mode("anchor")    
    ax.set_xlabel("/48 to /64 Suballocation Space")
    print("Saving figure")
    fig.savefig(outputfile,bbox_inches="tight", dpi=100)




def main():
    """
        Input: List of networks, Output: Heatmap of classified responses
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", required=True, type=str, help="File with IPv6 Prefixes")
    parser.add_argument("-m", "--measurementfolder", required=True,type=str,help="Path to folder with measurement files")
    parser.add_argument("-o", "--outputfile", required=True, type=str, help="Outputfile with heatmap")

    networks=read_networks(args.inputfile)

    # Generate the heatmap
    generate_heatmap_zmap(networks,args.measurementfolder,args.outputfile)




if __name__== "__main__":
    main()
