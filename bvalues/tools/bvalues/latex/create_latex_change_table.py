import json
import os
import numpy as np
from datetime import datetime, timedelta


# Define the vantage points and protocols
vantage_points = ['vantage1', 'vantage2']
protocols = ['icmpv6', 'tcp','udp'] # 'tcp_ack'
date_str=["2023_03_14","2023_03_15","2023_03_16","2023_03_17","2023_03_18"]
change_categories = ['bigger_one', 'only_one', 'all_empty']
change_labels = {
    'bigger_one': 'W. Ch.',
    'only_one': 'W/o. Ch.',
    'all_empty': '$\\varnothing$'
}

# Function to load data from JSON files
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to extract relevant data
def extract_relevant_data(data):
    return data['num_change_types']['all_empty'], data['num_change_types']['bigger_one'], data['num_change_types']['only_one']

def calculate_stats(values):
    mean = np.mean(values)
    std = np.std(values)
    return int(mean), int(std)

# Main function to process files and generate the table
def generate_table(path_to_json_files):
    # Dictionary to store results
    results = {vp: {prot: {cat: [] for cat in change_categories} for prot in protocols} for vp in vantage_points}
    for protocol in protocols:
         for vantage in vantage_points:
               for date_s in date_str:
                    file_name="bvalue_"+vantage+"/"+date_s+"/"+protocol+"/"+"bvalue_changes_counts.json"
                    print(file_name)
                    data = load_data(os.path.join(path_to_json_files, file_name))
                    all_empty, bigger_one, only_one = extract_relevant_data(data)
                    for cat in change_categories:
                         results[vantage][protocol][cat].append(data['num_change_types'][cat])
    
    # Calculate total for percentage calculation
    totals = {vp: {prot: sum(np.mean(results[vp][prot][cat]) for cat in change_categories) for prot in protocols} for vp in vantage_points}
    print(totals)
    # Create LaTeX table
    latex_content = r'\begin{table}[t]' + '\n'
    latex_content += r'    \renewcommand{\arraystretch}{1.4}' + '\n'
    latex_content += r'    \centering' + '\n'
    latex_content += r'    \scriptsize' + '\n'
    latex_content += r'    \begin{tabularx}{0.95\linewidth}{| p{0.2cm} | V R{0.7cm} p{0.4cm} V  | R{0.7cm} p{0.2cm} V |}' + '\n'
    latex_content += r'\cline{3-8}' + '\n'
    latex_content += r' \multicolumn{2}{c|}{} & \multicolumn{3}{c|}{Vantage 1 ($\sigma$)} & \multicolumn{3}{c|}{Vantage 2 ($\sigma$)}\\ \hline' + '\n'

    for cat in change_categories:
        latex_content += f'\\multirow{{{len(protocols)}}}{{*}}{{\\rotatebox{{90}}{{\\textbf{{{change_labels[cat]}}}}}}}'
        for protocol in protocols:
            row_data = []
            for vp in vantage_points:
                mean, std = calculate_stats(results[vp][protocol][cat])
                percentage = mean / totals[vp][protocol] if totals[vp][protocol] > 0 else 0
                row_data.append(f'{mean:,} & ({std}) & \\Chart{{{round(percentage,3)}}}')
            latex_content += f' & {protocol.upper()} & ' + ' & '.join(row_data) + ' \\\\ \n'
        latex_content += f'\\hline\n'

    latex_content += r'\end{tabularx}' + '\n'
    latex_content += r'{\raggedright \textit{NOTE:} \# of Networks $=$ mean and $\sigma$  $=$ standard deviation of five days.}' + '\n'
    latex_content += r'\captionof{table}{BValue Steps, networks with a change, without changes and networks that do not return ICMPv6 error messages. }' + '\n'
    latex_content += r'\label{tab:bvalue_step_changes}' + '\n'
    latex_content += r'\end{table}' + '\n'
    
    return latex_content


def main():

    # Configure the path to the directory containing the JSON files
    path_to_json_files = './vantage_counts/'

    # Print the latex table for BValue Steps
    latex_table = generate_table(path_to_json_files)
    print(latex_table)

if __name__== "__main__":
    main()
