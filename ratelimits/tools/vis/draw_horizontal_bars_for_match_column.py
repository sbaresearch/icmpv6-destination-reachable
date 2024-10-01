import pandas as pd 
import argparse
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['font.family'] = 'monospace'
rcParams['axes.facecolor'] = 'white'
rcParams['font.size']= 10
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42
# Update the function to place blue percentage labels on the negative side and increase offset
def create_diverging_barplot(red,total_red, blue, total_blue, filename):
    # Convert dictionaries to DataFrames
    my_cmap = list(plt.get_cmap("Dark2").colors)
    df_red = pd.DataFrame(list(red.items()), columns=['Category', 'Edge'])
    df_blue = pd.DataFrame(list(blue.items()), columns=['Category', 'Core'])
    
    # Merge the two DataFrames on 'Category'
    df = pd.merge(df_red, df_blue, on='Category', how='outer').fillna(0)
    
    # Sort the DataFrame based on the BlueValue in reversed order
    df = df.sort_values(by='Core')
    
    # Create the diverging bar plot with final adjustments to percentage labels
    fig, ax = plt.subplots(figsize=(6.5, len(df) * 0.22))
    
    bars_red = ax.barh(df['Category'], df['Edge'], color=my_cmap[2] , edgecolor='black', label='{:,}'.format(total_red)+" Centrality = 1") #color='salmon'
    bars_blue = ax.barh(df['Category'], -df['Core'], color=my_cmap[0], edgecolor='black', label='{:,}'.format(total_blue)+" Centrality > 1")  # Note the negative for blue # color='skyblue'
    
    # Adding percentage labels next to bars with increased offset and without minus sign for blue
    max_x=0
    for bar, value in zip(bars_red, df['Edge']):
        if bar.get_width() > max_x:
            max_x=bar.get_width()
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2, f"{value:.1f}%", 
                ha='left', va='center', color='black', fontsize=9)
    min_x=0
    for bar, value in zip(bars_blue,df['Core']):
        if bar.get_width() < min_x:
            min_x=bar.get_width()
        ax.text(bar.get_width() - 15, bar.get_y() + bar.get_height()/2, f"{value:.1f}%",ha='left', va='center', color='black', fontsize=9)

    # Add gridlines
    ax.yaxis.grid(True, linestyle='--', which='major', color='gray', alpha=0.5) 
    ax.xaxis.grid(True, linestyle='--', which='major', color='gray', alpha=0.5)  
    # Adding labels, title, and legend
    ax.set_xlabel('Percentage of routers')
    #ax.set_title('Diverging Bar Plot')
    ax.legend(loc="upper right",fontsize=8)
    
    # Set the adjusted x-axis limits
    ax.set_xlim(min_x-15, max_x+10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # Save the plot to the specified file
    plt.tight_layout()
    plt.savefig(filename)
    plt.show()


def normalize_100(inputdict):
	# Normalize the red values such that their sum is 100%
	sum_input = sum(inputdict.values())
	normalized_input = {key: (value / sum_input) * 100 for key, value in inputdict.items()}
	return normalized_input,sum_input


def preprocess_and_plot_horizontalbars_vendors(processedfile,outfile):

    df_processed=pd.read_csv(processedfile) 
    col="timeline_match_grouped"
    df_processed=df_processed.loc[(df_processed["saddr_matches_original_target"] == True)]
    df_processed.replace({"timeline_match_grouped":"unknow"},inplace=True)


    data_edge=df_processed.loc[(df_processed['centrality_count'] == 1)][col].value_counts().to_dict()
    data_core=df_processed.loc[(df_processed['centrality_count'] > 1)][col].value_counts().to_dict()

    data_edge_normalized,total_edge=normalize_100(data_edge)
    data_core_normalized,total_core=normalize_100(data_core)
    

    create_diverging_barplot(data_edge_normalized,total_edge,data_core_normalized,total_core,outfile)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--processedfile", required=False, default="data/data_ratelimits/matches.csv", type=str, help="CSV with processed Zmap Distances and Lab Matches")	
    parser.add_argument("-o", "--outfile", required=False, default="data/data_ratelimits/vendor_matches.pdf", type=str, help="CSV with processed Zmap Distances and Lab Matches")
    args=parser.parse_args()

    preprocess_and_plot_horizontalbars_vendors(args.processedfile,args.outfile)


if __name__ == "__main__":
    main()