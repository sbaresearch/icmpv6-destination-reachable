import json
import os
import numpy as np
from datetime import datetime


# Define the protocols and states
# Define the vantage points and protocols
vantage_points = ['vantage1', 'vantage2']
protocols = ['icmpv6', 'tcp', 'udp']
states = ['active',  'ambiguous','inactive']

# Function to load data from JSON files
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Define the protocols and states
protocols = ['icmpv6', 'tcp', 'udp']
date_str=["2023_03_14","2023_03_15","2023_03_16","2023_03_17","2023_03_18"]
# Function to load data from JSON files
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to calculate mean and standard deviation
def calculate_stats(values):
    mean = np.mean(values)
    std = np.std(values)
    return int(mean), int(std)

# Function to process files and generate the table
def generate_label_table(path_to_json_files):
	print(path_to_json_files)
    # Store results for each protocol, state, and labeled status (0 for active, 1 for inactive)
    results = {status: {prot: {state: [] for state in states} for prot in protocols} for status in ['0', '1']}

    for protocol in protocols:
         for vantage in vantage_points:
               for date_s in date_str:
                    file_name=protocol+"_"+vantage+"_"+date_s+"_bvalue_counts.json"
                    data = load_data(os.path.join(path_to_json_files, file_name))
                    for status in ['0', '1']:
                        for state in states:
                             # Extract counts for each state under each protocol and labeled status
                             count = data['response_types']['change'][status].get(state, 0)
                             results[status][protocol][state].append(count)

    # Calculate total for percentage calculation for each protocol
    totals = {status: {prot: sum(np.mean(results[status][prot][state]) for state in states) for prot in protocols} for status in ['0', '1']}
    print(totals)

    # Create LaTeX table
    latex_content = r'\begin{table}[t]' + '\n'
    latex_content += r'    \renewcommand{\arraystretch}{1.2}' + '\n'
    latex_content += r'    \centering' + '\n'
    latex_content += r'    \tiny' + '\n'
    latex_content += r'    \resizebox{\linewidth}{!}{' + '\n'
    latex_content += r'    \begin{tabular}{ | c| l r r r | r r r |}' + '\n'
    latex_content += r'\cline{3-8}' + '\n'
    latex_content += r' \multicolumn{2}{c}{} & \multicolumn{3}{|c|}{\textbf{labeled active}} & \multicolumn{3}{c|}{\textbf{labeled inactive}} \\ ' + '\n'
    latex_content += r' \multicolumn{2}{c}{}& \multicolumn{1}{|c}{Netw.} &  \multicolumn{1}{c}{$\sigma$} &  \multicolumn{1}{c|}{\%} & \multicolumn{1}{c}{Netw.} &  \multicolumn{1}{c}{$\sigma$} &  \multicolumn{1}{c|}{\%} \\ ' + '\n'
    latex_content += r' \hline' + '\n'

    for state in states:
        if state=="ambiguous":
            state_str="ambig."
        else:
            state_str=state
        latex_content += f'\\multirow{{3}}{{*}}{{\\rotatebox{{90}}{{\\textbf{{{state_str}}}}}}}'
        for protocol in protocols:
            row_data_active = []
            row_data_inactive = []
            for status in ['0', '1']:
                mean, std = calculate_stats(results[status][protocol][state])
                percentage = mean / totals[status][protocol] if totals[status][protocol] > 0 else 0
                data_point = f'{mean:,} & {std} & \\Chart{{{percentage:.3f}}}'
                if status == '0':
                    row_data_active.append(data_point)
                else:
                    row_data_inactive.append(data_point)
            latex_content += f' & {protocol.upper()} & ' + ' & '.join(row_data_active) + ' & ' + ' & '.join(row_data_inactive) + ' \\\\ \n'
        latex_content += r' \hline' + '\n'

    latex_content += r'    \end{tabular}}' + '\n'
    latex_content += r'    {\raggedright % $\ast$ ICMPv6 error messages not returned by default.  ' + '\n'
    latex_content += r'    NR\textsubscript{x} ... Vantage point 2 difference. $\sigma$ Standard deviation over five days.}' + '\n'
    latex_content += r'\captionof{table}{Error message classification for labeled networks.} ' + '\n'
    latex_content += r'    \label{tab:bvalues_active}' + '\n'
    latex_content += r'\end{table}' + '\n'
    
    return latex_content




def main():

    # Configure the path to the directory containing the JSON files
    path_to_json_files = './vantage_counts/'

    # Print the latex table for BValue Steps
    latex_table = generate_label_table(path_to_json_files)
    print(latex_table)

if __name__== "__main__":
    main()
