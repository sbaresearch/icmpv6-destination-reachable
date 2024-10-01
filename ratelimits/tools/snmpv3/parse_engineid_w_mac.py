import pandas as pd
from mac_vendor_lookup import MacLookup
import argparse
import nest_asyncio



def extract_snmpv3_info(engine_id,mac_db):
    """
    Extracts information from an SNMPv3 authoritative engine ID.

    Args:
    engine_id (str): The SNMPv3 authoritative engine ID as a string.

    Returns:
    tuple: A tuple containing the enterprise ID and the MAC address, if the message format is '03'.
    """

    # Extracting the enterprise ID (first 8 characters)
    enterprise_id = engine_id[:8].lstrip("8")
    try:
	    enterprise_id = int(enterprise_id, 16)
    except:
        print("Weird engineid format: "+str(engine_id))
        return "None","None"
    # Checking the message format (next 2 characters)
    message_format = engine_id[8:10]

   
    if len(engine_id)!=24 and len(engine_id) !=22:
         return enterprise_id, "None"
			
    # If message format is '03', extract the MAC address	
    if message_format == '03':
        mac_raw = engine_id[-12:]
        # Formatting the MAC address
        mac_address = ':'.join(mac_raw[i:i+2] for i in range(0, len(mac_raw), 2))
        return enterprise_id, mac_address.upper()
    else:
        return enterprise_id, "None"

# Test the function with the provided engine ID
def parse_engineid_file(inputfile,outputfile):
    nest_asyncio.apply()

    mac_db = MacLookup()
    mac_db.update_vendors()

    enterpriseid_dict={
        9:"cisco", \
        5842:"cisco-systems",\
        2636:"juniper", \
        2011:"huawei", \
        1991:"brocade", \
        6527:"nokia", \
        25506:"h3c", \
        3902:"zte", \
        11:"hpe",\
        14988:"mikrotik",\
        14823:"aruba",\
        30065:"arista",\
        664:"adtran",\
        26928:"aerohive",\
        21839:"alaxala",\
        4388:"alcatel",\
        6486:"alcatel", \
        2623:"asus",\
        6889:"avaya", \
        872:"avm",\
        6321:"calix",\
        674:"dell",\
        53526:"della-atc",\
        171:"d-link",\
        7367:"draytek",\
        52:"enterasys",\
        193:"ericsson",\
        1916:"extreme",\
        12356:"fortinet",\
        1411:"juniper-funk",\
        4874:"juniper-unisphere",\
        2356:"lancom",\
        3955:"linksys",\
        29671:"meraki",\
        4526:"netgear",\
        7483:"nokia-alcatel",\
        28458:"nokia-siemens",\
        32229:"nokia-novarra",\
        34326:"nokia-juhahopsu",\
        51450:"nokia-jeffdonnelly",\
        25053:"ruckus",\
        31322:"sierra",\
        46366:"technicolor",\
        11863:"tp-link",\
        28866:"trendnet",\
        41112:"ubiquiti",\
        21013:"xirrus",\
        12419:"yamaha",\
        890:"zyxel",\
        25461:"fw-paloalto",\
        3097:"fw-watchguard",\
        2620:"fw-checkpoint",\
        10704:"fw-barracuda",\
        47565:"fw-forcepoint",\
        8741:"fw-sonicwall",\
        42359:"fw-versanetworks", \
        2604:"fw-sophos",\
    }

    df_snmp=pd.read_csv(inputfile,sep=",",header=None,names=["src","engineid"])
    with open(outputfile,"w") as f_out:
           f_out.write("src;engineid;enterpriseid;vendor;mac;macvendor\n")
           for row in df_snmp.itertuples():
               vendor="None"
               mac_vendor="None"
               src=row.src
               engineid=row.engineid
               enterpriseid,mac=extract_snmpv3_info(engineid,mac_db)
               try:
                   vendor=enterpriseid_dict[enterpriseid]
               except:
                   vendor="unknown"
               if mac != "None":
                   try:	
                       mac_vendor=mac_db.lookup(mac).replace(","," ")
                   except:
                       mac_vendor="unknown"
               #print(src+";"+str(enterpriseid)+";"+vendor+";"+mac+";"+mac_vendor)
               f_out.write(src+";"+engineid+";"+str(enterpriseid)+";"+vendor+";"+mac+";"+mac_vendor+"\n")
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", default="targets_with_engineid.csv", required=False, type=str, help="<filepath> File with IPv6 Address,EngineID")
    parser.add_argument("-o", "--outputfile", default="targets_with_snmpv3_and_mac_vendors.csv", required=False, type=str, help="<filepath> File to store the parsed vendors")
    args = parser.parse_args()  

    parse_engineid_file(args.inputfile,args.outputfile)

if __name__ == "__main__":
    # your main function call here
    main()