import os
import json
from datetime import datetime, timedelta

# Constants
START_DATE = datetime(2023, 3, 14)
END_DATE = datetime(2023, 3, 18)
BASE_PATH = 'vantage_counts/'  
PROTOCOLS = ['icmpv6', 'tcp', 'udp']  

def date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def read_json_data(protocol, date):
    file_path = os.path.join(BASE_PATH, f'{protocol}_vantage1_{date.strftime("%Y_%m_%d")}_bvalue_counts.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get('count_msgtypes', {})
    return {}

def main():
    # Initialize results dictionary for each protocol, response number, and message type count
    results = {protocol: {str(resp_num): {str(i): [] for i in range(1,6)} for resp_num in range(0, 6)} for protocol in PROTOCOLS}
    print(results)
    # Collect data
    for date in date_range(START_DATE, END_DATE):
        for protocol in PROTOCOLS:
            data = read_json_data(protocol, date)
            for resp_num_str, msg_types in data.items():
                for msg_type_str, count in msg_types.items():                    
                    results[protocol][resp_num_str][msg_type_str].append(count)

    # Calculate means
    mean_results = {protocol: {str(resp_num): {str(i): [] for i in range(1,6)} for resp_num in range(0, 6)} for protocol in PROTOCOLS}
    for protocol in PROTOCOLS:
        for resp_num in range(0, 6):
            resp_num_str = str(resp_num)
            for msg_type in range(1,6):
                msg_type_str = str(msg_type)
                values = results[protocol][resp_num_str][msg_type_str]
                mean_results[protocol][resp_num_str][msg_type_str] = sum(values) // len(values) if values else 0


    print(mean_results)
    # Output LaTeX table
    print("\\begin{table}")
    print("\\begin{tiny}")
    print("\\begin{tabular}{cc|c||c|c|c|c|c|c|}")
    print("& & &  \\multicolumn{5}{c|}{No. of responses} \\\\")
    print("& & Protocol & 1 & 2 & 3 & 4 & 5 \\\\ \\hline \\hline")
    for msg_type in range(1, 6):  # Message types
        for protocol in PROTOCOLS:
            counts=""
            row_label = f"& {msg_type} & {protocol.upper()}"
            for resp_num in range(1,6):                
                counts += ' & ' + str(mean_results[protocol][str(resp_num)][str(msg_type)])
            print(f"{row_label} {counts} \\\\")
            if protocol == PROTOCOLS[-1]:
                print("\\cline{2-8}")
    print("\\end{tabular}")
    print("\\end{tiny}")
    print("\\caption{Mean No. of BValues wrt no. of received responses and no. of message types.}")
    print("\\label{table:mean_subnet_responses_matrix}")
    print("\\end{table}")




if __name__ == "__main__":
    main()
