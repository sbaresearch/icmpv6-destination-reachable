import pandas as pd


def reduce_vendors(inputfile,outputfile):
	vendor_mappings={
		"3COM EUROPE LTD":"enterpriseid",
		"Adtran Inc":"adtran",
		"Alcatel-Lucent Enterprise":"alcatel",
		"Avaya Inc":"enterpriseid",
		"Brocade Communications Systems LLC":"brocade",
		"China Mobile Group Device Co. Ltd.":"enterpriseid",
		"Cisco-Linksys  LLC":"cisco-linksys",
		"Cisco Systems  Inc":"cisco",
		"COMDA ENTERPRISES CORP.":"enterpriseid",
		"CZ.NIC  z.s.p.o.":"enterpriseid",
		"Dell Inc.":"dell",
		"D-Link International":"d-link",
		"DR. B. STRUCK":"enterpriseid",
		"Edgecore Networks Corporation":"enterpriseid",
		"EQUIP'TRANS":"enterpriseid",
		"Extreme Networks Headquarters":"extreme",
		"FERRAN SCIENTIFIC  INC.":"enterpriseid",
		"FS COM INC":"enterpriseid",
		"FUJIAN STAR-NET COMMUNICATION CO. LTD":"enterpriseid",
		"Hangzhou H3C Technologies Co.  Limited":"h3c",
		"Hewlett Packard":"hpe",
		"Hewlett Packard Enterprise":"hpe",
		"HUAWEI TECHNOLOGIES CO. LTD":"huawei",
		"Inspur Group Co.  Ltd.":"enterpriseid",
		"Juniper Networks":"juniper",
		"Madge Ltd.":"enterpriseid",
		"NETGEAR":"netgear",
		"None":"enterpriseid",
		"OneAccess SA":"enterpriseid",
		"PENTACOM LTD.":"enterpriseid",
		"Raisecom Technology CO.  LTD":"raisecom",
		"Ruckus Wireless":"ruckus",
		"Ruijie Networks Co. LTD":"enterpriseid",
		"Super Micro Computer  Inc.":"supermicro",
		"TEKNOR MICROSYSTEME  INC.":"enterpriseid",
		"TERACOM TELEMATICA S.A":"enterpriseid",
		"Ufispace Co.  LTD.":"enterpriseid",
		"unknown":"enterpriseid",
		"VMware  Inc.":"enterpriseid",
		"VST TECHNOLOGIES  INC.":"enterpriseid",
		"XEROX CORPORATION":"enterpriseid",
		"zte corporation":"zte"
	}

	df_snmpv3=pd.read_csv(inputfile,sep=";")
	# Itertuples
	conflicts=0
	with open(outputfile,'w') as f:
		f.write("src,vendor,mactrue\n")
		for row in df_snmpv3.itertuples():
			
			#EnterpriseID Vendor
			enterpriseid_vendor=row.vendor
			#Mac Vendor	
			mac_vendor=row.macvendor
			if pd.isnull(mac_vendor):
				mac_vendor="enterpriseid"
			else:
				mac_vendor=vendor_mappings[mac_vendor]
			
			if mac_vendor!="enterpriseid":
			
				f.write(row.src+","+mac_vendor+",True\n")
				# Count conflicts
				if mac_vendor!=enterpriseid_vendor:
					conflicts+=1
			else:
				
				f.write(row.src+","+enterpriseid_vendor+",False\n")
	print("Conflicts: "+str(conflicts))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", default="targets_with_snmpv3_and_mac_vendors.csv", required=False, type=str, help="<filepath> File with IPv6 Address;EngineID;EnterpriseID;Vendor;MAC;MAC_Vendor")
    parser.add_argument("-o", "--outputfile", default="targets_with_vendor.csv", required=False, type=str, help="<filepath> File to store the parsed vendors")
    args = parser.parse_args()  

    reduce_vendors(args.inputfile,args.outputfile)

if __name__ == "__main__":
    # your main function call here
    main()