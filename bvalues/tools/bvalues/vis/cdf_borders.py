import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import json
from empiricaldist import Cdf

plt.style.use("bmh")
rcParams['font.family'] = 'monospace'
rcParams['axes.facecolor'] = 'white'
rcParams['font.size']= 12
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42

def extract_sizes(changes, network):
    sizes = []
    for change in changes[1:5]:  # Only consider up to the first three changes
        if 'bvalue' in change:
            bvalue = int(change['bvalue'][1:]) # Convert B<value> 
            if bvalue == 120:
                bvalue+=7
            else:
                bvalue+=8
            sizes.append(bvalue)
    if network:
        prefix_size = int(network.split('/')[1])  # Split the network and take the prefix size
        sizes.insert(0, prefix_size)
    #if len(sizes)==1:
    #	sizes.append(prefix_size)
    #	print(sizes)
    return sizes

def plot_cdfs(data):
    my_cmap = list(plt.get_cmap("Dark2").colors)
    my_cmap[3]="black"
    cmap_map={0:0,1:1,2:2,3:3}
    line_map={0:0,1:2,2:3,3:1}
    linetypes = ["solid", "dotted", "dashed", "dashdot"]
    fig, ax = plt.subplots(figsize=(5.5,2.5))

    for idx, key in enumerate(data):

        cdf = Cdf.from_seq(data[key])
        qs = np.insert(cdf.qs, 0,0)  # Insert 0 at the beginning of quantiles
        ps = np.insert(cdf.ps, 0,0)  # Insert 0 at the beginning of probabilities
        #print(str(idx)+","+)
        
        #if idx==0:
        #    print(qs)
        #    print(ps)

        plt.step(qs, ps, where='post', color=my_cmap[cmap_map[idx]], linewidth=1.8, label=key, linestyle=linetypes[line_map[idx]], alpha=0.9)

    plt.xlim([0, 128])
    plt.xticks(np.arange(0, 144, 16))
    plt.legend(loc='lower right')
    plt.xlabel("BValue Size", fontsize=14)
    plt.ylabel("CDF", fontsize=14)

    plt.savefig("network_borders_cdf_reproduced.pdf", bbox_inches='tight', dpi=300)
    plt.show()
    plt.clf()

def main():
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    # Dictionary to hold all sizes for plotting CDFs
    cdf_data = {'First Change': [], 'Second Change': [], 'Third Change': [],'BGP Border':[]}
    
    # Extract and organize the data from JSON
    for network, targets in data.items():
        for target, changes in targets.items():
            sizes = extract_sizes(changes, network)
            if len(sizes) > 1:
                cdf_data['BGP Border'].append(sizes[0])
            if len(sizes) > 2:
                cdf_data['First Change'].append(sizes[1])
            if len(sizes) > 3:
                cdf_data['Second Change'].append(sizes[2])
            if len(sizes) > 3:
                cdf_data['Third Change'].append(sizes[3])
    
    
    # Plot the CDFs
    plot_cdfs(cdf_data)

if __name__ == '__main__':
    main()
