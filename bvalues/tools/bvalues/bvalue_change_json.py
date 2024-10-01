import argparse
import json
from natsort import natsorted
import pprint
import math
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# BVALUE FILTER FLAGS
flag_src_addr_changes = False  # True impacts the number of changes caused by hitting other alive subnets, load balancing
flag_error_wins_over_empty = True  # True: Kills random hits better, False: Treats low responding networks worse
flag_skip_positive_responses = True
flag_split_major_type_across_nrsrces = True  # True: Kills random hits better, False: Treats low responding networks worse
flag_do_not_count_message_types_for_b127 = True # True: Avoid counting B127 message types and response types where we sent a single request

zmap_type_dict = {
    "none": "Filter_None",
    "echoreply": "Filter_Echo",
    "empty": "Filter_Empty",
    "toobig": "Filter_Toobig",
    "fragment": "Filter_Fragment",
    "other": "Filter_Other",
    "paramprob": "Filter_Param",
    "udp": "Filter_UDP",
    "rst": "Filter_RST",
    "synack": "Filter_SA",
    "timxceed": "inactive",
    "unreach_addr": "inactive",
    "unreach_addr_nonfiltered": "active",
    "unreach_admin": "ambiguous",
    "unreach_noport": "ambiguous",
    "unreach_noroute": "ambiguous",
    "unreach_policy": "ambiguous",
    "unreach_rejectroute": "inactive"
}

def pick_major(bvalue, counts, blocklist={"echoreply", "synack", "rst", "udp"}):
    major_responses = {}
    max_count = 0

    for resp_type, details in bvalue.items():
        if flag_skip_positive_responses:
            if resp_type in blocklist:
                continue
        if flag_error_wins_over_empty:
            if resp_type == "empty" and any(r not in blocklist for r in bvalue if r != "empty"):
                continue
        count = details.get('count', 0)
        if flag_split_major_type_across_nrsrces:
            count = math.ceil(count / len(details["srces"]))
        if count > max_count:
            max_count = count
            major_responses = {resp_type: details}
        elif count == max_count:
            major_responses[resp_type] = details
    return major_responses

def calculate_ttl_at_destination(ttl, ttl_at_target):
    if ttl == -1 or ttl_at_target == -1:
        return -1
    return ttl + 255 - ttl_at_target

def extract_info(major, bvalue):
    for resp_type, details in major.items():
        srces = set(details.get('srces', []))
        ttl = int(details.get('ttl', -1))
        ttl_at_target = int(details.get('ttl_at_target', -1))
        ttl_at_dest = calculate_ttl_at_destination(ttl, ttl_at_target)

        info = {
            "type": resp_type,
            "bvalue": bvalue,
            "count": details["count"],
            "rtt": details["rtt"],
            "srces": set(sorted(srces)),
            "ttl_at_dest": ttl_at_dest,
            "same_bits": ', '.join(map(str, details.get('same_bits', []))),
        }
        return info

def compare_bvalue_steps(bvalue_step1, bvalue_step2, curr_bvalue, counts, compare_to_first=False):
    if not compare_to_first:
        major1 = pick_major(bvalue_step1, counts)
    else:
        major1 = {}
        major1[bvalue_step1["type"]] = bvalue_step1
    major2 = pick_major(bvalue_step2, counts)

    changes = []
    if len(major1) > 1 or len(major2) > 1:
        counts["bvalues_with_response_ties"] += 1
        return changes

    src_set = set()
    for resp_type, detail in major1.items():
        for src in detail["srces"]:
            src_set.add(src)

    for resp_type, details in major2.items():
        srces = set(details.get('srces', []))
        change_dict = {"type": False, "src": False}
        if resp_type not in major1:
            change_dict["type"] = True
            counts["change_type"] += 1
        if len(src_set.intersection(srces)) == 0:
            if flag_src_addr_changes:
                change_dict["src"] = True
            counts["change_src"] += 1

        if change_dict["type"] or change_dict["src"]:
            change_info = extract_info(major2, curr_bvalue)
            change_info["change_type"] = change_dict["type"]
            change_info["change_src"] = change_dict["src"]
            changes.append(change_info)

    return changes

def build_history(bvalues, sorted_bvalues):
    response_history = {}
    for bvalue in sorted_bvalues:
        responses = bvalues[bvalue]
        for resp_type, details in responses.items():
            srces = set(details.get('srces', []))
            if resp_type not in response_history:
                response_history[resp_type] = []
            response_history[resp_type].append((srces, bvalue))
    return response_history

def pick_first_bvalue(bvalues, sorted_bvalues, counts):
    B127 = True
    first_info = {}
    for bvalue in sorted_bvalues:
        curr_bvalue = bvalues[bvalue]
        major = pick_major(curr_bvalue, counts)
        if len(major) == 1:
            first_info = extract_info(major, bvalue)
            if B127 and first_info["type"] == "empty":
                B127 = False
                continue
            break
        else:
            continue
    return first_info

def check_temporary(last_major, bvalues, bvalues_sorted, counts):
    temporary = False
    for bvalue in bvalues_sorted:
        current_bvalue_step = bvalues[bvalue]
        changes = compare_bvalue_steps(last_major, current_bvalue_step, bvalue, counts, compare_to_first=True)
        if not changes:
            temporary = True
    return temporary

def update_message_type_and_responses_count(bvalues, message_type_and_responses_count):
    for bvalue, responses in bvalues.items():
        
        if bvalue=="B127":
            if flag_do_not_count_message_types_for_b127:
                continue

        message_count = sum(1 for _, details in responses.items() if details['count'] > 0 and _ != 'empty')
        for response_type, details in responses.items():
            # Only count all empty
            if message_count != 0 and response_type == 'empty':
                continue
            # Do not count response types with 0
            if details['count'] == 0:
                continue
            count = details['count']
            count = min(count, 5)
            if message_count in message_type_and_responses_count[count]:
                message_type_and_responses_count[count][message_count] += 1
            else:
                message_type_and_responses_count[count][message_count] = 1

def process_bvalues(bvalues, counts, message_type_and_responses_count):
    sorted_bvalues = natsorted(bvalues.keys(), reverse=True)
    major_bvalues = []

    update_message_type_and_responses_count(bvalues, message_type_and_responses_count)

    first = pick_first_bvalue(bvalues, sorted_bvalues, counts)
    if not first:
        logger.debug("Could not determine any bvalue (aliasing)")
        logger.debug(bvalues)
        return major_bvalues
    major_bvalues.append(first)
    for bvalue in sorted_bvalues[sorted_bvalues.index(first['bvalue']) + 1:]:
        current_bvalue_step = bvalues[bvalue]
        changes = compare_bvalue_steps(major_bvalues[-1], current_bvalue_step, bvalue, counts, compare_to_first=True)
        temporary_change = check_temporary(major_bvalues[-1], bvalues, sorted_bvalues[sorted_bvalues.index(bvalue) + 1:], counts)
        if changes and not temporary_change:
            major_bvalues.extend(changes)

    return major_bvalues

def detect_changes(data):
    counts = {
        "bvalues_with_response_ties": 0,
        "change_type": 0,
        "change_src": 0,
        "num_changes": {},
        "num_change_types": {"all_empty": 0, "bigger_one": 0, "only_one": 0},
        "total_networks": 0,
        "hitlist_responsive": 0
    }
    message_type_and_responses_count = {i: {j: 0 for j in range(1, 6)} for i in range(6)}
    results = {}

    for network, info in data.items():
        results[network] = {}
        targets = info.get('targets', {})
        counts["total_networks"] += 1
        for target, target_details in targets.items():
            if target_details["hitlist_responsive"] != 1:
                continue
            counts["hitlist_responsive"] += 1
            bvalues = target_details.get('bvalues', {})
            results[network][target] = process_bvalues(bvalues, counts, message_type_and_responses_count)

            if len(results[network][target]) > 0:
                for i, major_bvalue in enumerate(results[network][target]):
                    results[network][target][i]["srces"] = ",".join(results[network][target][i]["srces"])

            num_changes = len(results[network][target])
            if num_changes in counts["num_changes"]:
                counts["num_changes"][num_changes] += 1
            else:
                counts["num_changes"][num_changes] = 1

            if num_changes == 1:
                if results[network][target][0]["type"] == "empty":
                    counts["num_change_types"]["all_empty"] += 1
                else:
                    counts["num_change_types"]["only_one"] += 1
            else:
                counts["num_change_types"]["bigger_one"] += 1

    return results, counts, message_type_and_responses_count

def create_eval_counts(results, counts, message_type_and_responses_count):
    counts["count_msgtypes"] = message_type_and_responses_count
    major_types_counted = {}

    for net in results:
        for target in results[net]:
            tag = "no_change" if len(results[net][target]) == 1 else "change"
            if tag not in major_types_counted:
                major_types_counted[tag] = {}
            for id, change in enumerate(results[net][target]):
                type = results[net][target][id]["type"]
                if id not in major_types_counted[tag]:
                    major_types_counted[tag][id] = {x: 0 for x in zmap_type_dict.keys()}
                    major_types_counted[tag][id]["active"] = 0
                    major_types_counted[tag][id]["inactive"] = 0
                    major_types_counted[tag][id]["ambiguous"] = 0
                    major_types_counted[tag][id]["change_src"] = 0
                    major_types_counted[tag][id]["change_type"] = 0
                major_types_counted[tag][id][type] += 1

                classifier = zmap_type_dict.get(type, None)
                if classifier and "Filter" not in classifier:
                    major_types_counted[tag][id][classifier] += 1
                if results[net][target][id].get("change_type"):
                    major_types_counted[tag][id]["change_type"] += 1
                if results[net][target][id].get("change_src"):
                    major_types_counted[tag][id]["change_src"] += 1

    counts["response_types"] = major_types_counted

def main():
    global flag_split_major_type_across_nrsrces
    global flag_src_addr_changes
    global flag_error_wins_over_empty
    global flag_skip_positive_responses

    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json-file", required=True, type=str, help="Path to BValue Json")
    parser.add_argument("-o", "--output-file", required=False, default="bvalue_changes.json", type=str, help="Path to BValue Change Json")
    parser.add_argument("-c", "--count-file", required=False, default="bvalue_changes_counts.json", type=str, help="Path to BValue Change Counts Json")
    parser.add_argument("-s", "--src-flag", action='store_true', help="Evaluate Src address changes in addition to response type changes)")
    parser.add_argument("-e", "--empty-flag", action='store_false', help="Disable preferring error messages over empty bvalue steps")
    args = parser.parse_args()

    if args.src_flag:
        print("Evaluating src address changes:")
        flag_src_addr_changes = args.src_flag
    if args.empty_flag:
        flag_error_wins_over_empty = args.empty_flag

    with open(args.json_file, 'r') as f_json:
        bvalue_dict = json.load(f_json)

    results, counts, message_type_and_responses_count = detect_changes(bvalue_dict)
    create_eval_counts(results, counts, message_type_and_responses_count)

    with open(args.output_file, "w") as f:
        json.dump(results, f, indent=4)

    with open(args.count_file, "w") as f:
        json.dump(counts, f, indent=4)

if __name__ == "__main__":
    main()
