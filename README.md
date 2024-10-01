![logo](/run/user/1000/gvfs/sftp:host=aim/home/florian/2024/destination-reachable/logo.png)

# Code for Active Measurements on ICMPv6 Error Messages

The toolchain evaluates the ICMPv6 error message **type & code usage** and ICMPv6 error message **rate limit** implementations of IPv6 routers. 

It allows to evaluate the implementation of the following  ICMPv6 Error Message Types & Codes:

| Type | Name                    | Code  | Name                        | Abbr.  |
| ---- | ----------------------- | ----- | --------------------------- | ------ |
| 1    | Destination Unreachable | 0     | No Route                    | NR     |
|      |                         | 1     | Administratively Prohibited | AP     |
|      |                         | ~~2~~ | ~~Beyond Scope~~            | ~~BS~~ |
|      |                         | 3     | Address Unreachable         | AU     |
|      |                         | 4     | Port Unreachable            | PU     |
|      |                         | 5     | Failed Policy               | FP     |
|      |                         | 6     | Reject Route                | RR     |
| 3    | Time Exceeded           | 0     | Hop Limit Exceeded          | TX     |

> [!IMPORTANT]
>
> The code offers the possibility to:
>
> 1. reproduce our results using our measurement datasets.
> 2. replicate our methodology with different targets and vantage points.
>
> **What it is not**: It is not a complete one-script/docker solution, since measurements were conducted in different environments (GNS3 router images, kvm kernel testing, active measurements on routers in the IPv6 Internet)

## 📚 Publication

```bibtex
@inproceedings{holzbauer2024reachable,
  title     = {Destination Reachable: What ICMPv6 Error Messages Reveal About Their Sources},
  author    = {Florian Holzbauer and Markus Maier and Johanna Ullrich},
  booktitle = {Proceedings of the 2024 ACM Internet Measurement Conference (IMC '24)},
  year      = {2024},
  location  = {Madrid, Spain},
  pages     = {1--15},
  publisher = {ACM},
  doi       = {10.1145/3646547.3688420},
}
```

## 👩‍💻👨‍💻 Authors

The authors are part of the [Network & Critical Infrastructure Security Group@SBA Research](https://www.sba-research.org/research/research-groups/eris/) and [SEC@University of Vienna](https://sec.cs.univie.ac.at/).

## 📓 Jupyter Notebooks

To allow easier orchestration of our tools, we provide two Jupyter Notebooks. Create the virtual environment, install the dependencies and the kernel to execute the notebooks.

**Requirements**

```bash
python3 -m venv env_icmpv6
# Windows: !<env_name>\Scripts\activate
source env_icmpv6/bin/activate
pip install -r requirements.txt
ipython kernel install --name "venv-icmpv6" --user
```

Run Jupyter Notebook (Read Important: Change Kernel -> venv-icmpv6)

```bash
# Execute locally
jupyter notebook --no-browser --port=9999 # Save Token
# Open Browser with: http://localhost:9999 and enter Token
```

To run the jupyter notebook on a remote location/server (Read Important: Change Kernel -> venv-icmpv6):

```bash
# Execute on server
jupyter notebook --no-browser --port=9999 # Save Token
# Execute locally
ssh -NfL localhost:9999:localhost:9999 <user>@<server>
# Open Browser with: http://localhost:9999 and enter Token
```

> [!IMPORTANT]
>
> You should now be able to see your kernel in the IPython notebook menu:   `Kernel -> Change kernel` and be able to switch to it (you may need to   refresh the page before it appears in the list). IPython will remember   which kernel to use for that notebook from then on.

## ⚙️ Methodology

### 1.  Response Types and Codes

In the first step we classify the error message type and code usage of IPv6 routers to infer routing scenarios.

#### 1.1 Routerlab 🔬 (**Prestep - Not covered by the Jupyter Notebook**)

 From our [router lab](https://github.com/sbaresearch/router-lab) we extract ICMPv6 error message default behavior for 15 routers and firewalls from 11 vendors.  To verify if routers in the IPv6 Internet are behaving accordingly we introduce BValue Steps.

The table shows the returned error message types under six different routing scenarios derived from RFC4443. We list the expected scenarios for each response type in brackets.

| Scenario &nbsp; &nbsp; | Active Network | Inactive Network | Active Netw. ACL | Inactive Netw. ACL | Null Route | Routing Loop |
| ---------------------- | -------------- | ---------------- | ---------------- | ------------------ | ---------- | ------------ |
| NR (S2)                | ○ 0            | ● 14             | ● 1              | ● 2                | ● 2        | ○ 0          |
| AP (S3,S4)             | ○ 0            | ○ 0              | ● 4              | ● 5                | ● 3        | ○ 0          |
| AU (S1)                | ● 14           | ○ 0              | ○ 0              | ○ 0                | ● 1        | ○ 0          |
| PU ()                  | ○ 0            | ○ 0              | ● 3              | ● 2                | ○ 0        | ○ 0          |
| FP (S3,S4)             | ○ 0            | ● 1              | ● 1              | ● 2                | ○ 0        | ○ 0          |
| RR (S5)                | ○ 0            | ○ 0              | ○ 0              | ○ 0                | ● 2        | ○ 0          |
| TX (S6)                | ○ 0            | ○ 0              | ○ 0              | ○ 0                | ○ 0        | ● 15         |
| ∅                      | ● 1            | ○ 0              | ● 4              | ● 3                | ● 9        | ○ 0          |

> NOTE: Number = # of routers that return the error message type in a scenario; a single RUT can return multiple error message types if more than one configuration option is available.

-------------------------

#### 1.2 BValue Steps 👣

`Path: bvalues` and `measurements/type_and_codes/bvalues`

are used to collect ICMPv6 error messages for routers/networks in the IPv6  Internet.

To collect error messages for active and inactive networks in the IPv6 Internet, we rely on BValue Steps. To do so BValue Steps derive unassigned IPs from responsive IPv6 addresses.

BValue Steps traverse the target network space in steps of x bits (=8 by default). For each step 5 addresses with random IIDs are generated. This is an address seeded algorithm that requires a list of IPv6 addresses as input. In our work we relied on the [IPv6 hitlist service](https://ipv6hitlist.github.io).

We rely on routing collectors to assign routed network borders to each hitlist address. For each routed network, we choose one exemplary hitlist address to represent the network to avoid bias by networks with many addresses in the hitlist.

B127 is at the moment implemented as a separate measurement that only flips the last bit. The results are then combined with the results of the regular BValue Steps Measurement.

> [!TIP]
>
> To again verify if the responsive address is responsive to either or all ICMPv6, TCP and UDP, lastbit writes the original and the flipped address to the output file.

> [!IMPORTANT]
>
> Add-ons developed since the paper version:
>
> 1. Check whether hitlist addresses map to ::/0 and avoid such prefixes
> 2. Add-on (in progress): Create pseudo-random addresses where the first bit of the BValue step is flipped and the remaining are random bits to avoid partial overlaps.

##### E.g. Bvalue Address Generation

<img src="/run/user/1000/gvfs/sftp:host=aim/home/florian/2023/PAPER_Toolset/types_and_codes/bvalue/bvalue_example.png" alt="BValue Example" style="height:200px;" />

#### 1.3 Network Activity Scans 🌐 (Follow up step -  Not covered  by the Jupyter Notebook)

`Path: measurements/types_and_codes/network_activity_scans`

##### - IPv6 Internet at /48 granularity. 

We use statistic sampling to traceroute, measure paths to every possible routed /48 using YARRP. If a prefix is larger than /48, e.g. a /32 prefix will be slit into 2^16 /48 prefixes. If in that /32 prefix the suballocation size is /64, we would scan 2^16 out of 2^32 /64 prefixes, that is what is referred to as statistical sampling. That means for a routed /48 one traceroute will be performed (Hop limit: 5 to 25) while for a /32 2^16 traceroutes have to be performed.  We extract all the sources that returned an error message for a destination, which are then serving as input for the rate limiting measurement.

> [!IMPORTANT]
>
> 1) We filter 6to4 (2002::/16) which includes 4.3Mrd /48s, based on Google statistics the amount of traffic originating from this range is very low.
> 2) We do not fully cover BGP-announced prefixes that are less specific than /24. In a first step, we evaluate whether more specific prefixes are announced. All prefixes that do not do so, we subject to an ICMPv6 prescan and reduce them to promising /24s. For this, we scan 2 addresses per included /32 (the first one and a random one) and take /24s for which we receive responses. If no response is received, we manually select four /24s. In March 2024, there were 32 prefixes (5.4 billion /48s) in rv6 (RouteViews) affected by this—13 of them have not announced any more specific prefixes and will be subjected to the prescan.

The yarrp-toolchain is not published within this repository. This repository will be updated as soon as the tracerouting-toolchain is publicly available.

Based on the number of paths a router resides on we calculate a centrality score. 

- Centrality Score of 1 ... Router serves a single path - most likely a small to medium sized router on the edge of the Internet
- Centrality Score > 1 ... Router serves multiple paths - the router is more likely to be an enterprise/core route

| Measured /48s | 5,016,400,232 (100%) |
| ------------- | -------------------- |
| Responsive    | 616,417,709          |
| Unresponsive  | 4,399,982,523        |

| Responsive |                     |
| ---------- | ------------------- |
| Active     | 83,248,768 (13.5%)  |
| Ambiguous  | 191,948,361 (31%)   |
| Inactive   | 341,220,580 (55.5%) |

##### - Enumerating /64 networks inside routed /48s

We rely on ZMap to send request every /64 in all BGP announced /48s (we ignore allocations less specific than /48 in this measurement).  Through this we explicitly want to classify error messages for the IPv6 periphery.

We rely on `gen_48_subs.py` to generate the target addresses and `shuf` and `split --line-bytes 20G` to split them into equally sized target files which are scanned with `scan_zmap.sh`. 

| Measured /64s | 6,085,410,816 (100%)  |
| ------------- | --------------------- |
| Responsive    | 1,368,371,825 (22.5%) |
| Unresponsive  | 4,717,038,991 (77.5%) |

| Responsive |                   |
| ---------- | ----------------- |
| Active     | 355,616,627 (26%) |
| Ambiguous  | 209,970,342 (15%) |
| Inactive   | 802,784,856 (59%) |

### 2. Rate Limits ⌛

`Path: ratelimits` and `measurements/ratelimits`

The Jupyter Notebook covers the **evaluation** of the TX rate limits in the IPv6 Internet, the extraction of SNMPv3 labels and the matching of the ICMPv6 rates to the vendor/kernel defaults. 

Active measurements are not covered as they are orchestrated through bash scripts.

#### 2.1 Ratelimits Router Lab 🔬

 **(Not covered by the Jupyter Notebook, see Measurements section)**

`Path: measurements/ratelimits/routerlab`

Sets of Tools to measure the rate limit of the 15 router and firewall appliances in the GNS3 lab (**AU_long, NR, TX**).

Includes a bash script to send packets to the target router from the GNS3 server over a TUN/TAP interface.

`./orchestrate_nd_rate_limits_single_destination.sh <routerid (1..f)> <routermac> <protocols (all)> <title (paper)> <scanrate (200)> <duration (10)>`

#### 2.2  Kernel Defaults 🐧

**(Not covered by the Jupyter Notebook, see Measurements section)**

`Path: measurements/ratelimits/kerneldefaults/kvm`

Rate limits are first defined in the kernel, based on the HZ (Number of interrupts during 1000ms) - we measure kernel default ICMP and ICMPv6 rate limits based on Debian Live images inside kvm which we can automate over the serial console. 

`bash linux_kernel_measurement.sh`

1. Download Debian Live Image from https://cdimage.debian.org/mirror/cdimage/archive/
2. Runs live image through kvm, establishes FIFO connection over serial console, calls `orchestrate_kvm_scan.sh`
3. `orchestrate_kvm_scan.sh` uses zmap_reqnr_single to send packets to the vm and originate error messages

#### 2.3 Enumerating TX Rate Limits in the IPv6 Internet 🌐

**(Not covered by the Jupyter Notebook, see Measurements section)**

`Path: measurements/ratelimits/routerscan`

To trigger TX responses from a router the input requires a destination on which the router is on path at the specified hop, counted from your vantage point.   

> [!IMPORTANT]
>
> What we noticed is that the packet timings in ZMap when starting multiple ZMap instances are off.  Therefore we adapted the zmap timing algorithm to not use the default mode. You can use this version if you want to enumerate multiple routers in parallel. The necessary bash script to administrate such a scan can be found under:
>
> *Bash Script: measurements/ratelimits/routerscan/scan_single_vantage.sh*
>
> By default the script launches 20 router measurements in parallel
>
> *ZMap: zmap_versions/zmap_reqnr_parallel.zip*

```
Requires: zmap_reqnr_parallel.zip
Input Format:
router,destination,hops
Output:
router1.csv
router2.csv
...
```

##### 2.3.1. SNMPV3  Vendor Labels 🏷️ as Ground Truth 

**(Not fully covered by the Jupyter Notebook, data not provided as SNMPv3 includes sensitive data and is registration first)**

Steps to reproduce, follow the steps in the Jupyter Notebook:

1. Request vendor information of IPv6 routers from SNMPv3 vendor labels provided by this [service](https://snmpv3.io/).

2. Reduce the SNMPv3 data to routers with known number of hops from the vantage point and a target address behind the router to collect TX error rates (Data not publicly available, data on request or perform your own traceroutes) 

   The Jupyter Notebook includes code to filter the files.

3. Use the following  bash snippet to extract the AuthoritativeEngineID from the SNMPv3

   For this we need access to scans from [snmpv3.io](https://snmpv3.io/): e.g. 2023-09-28-udp161-snmpv3.csv  
   From there we extract the src (Field 1) and the snmpv3 data (ASN1 encoded)   
   We use text2pcap and tshark to parse the snmpv3 data (slow!) 
   The following bash script does the job (24h+ needed)

   > [!TIP]
   >
   > May take some time, execute snippet inside `screen`

   Requires: 

   ```bash
   sudo apt install tshark
   sudo apt install text2pcap
   ```

   ```bash
   var=""
   time while IFS="," read src data; do	
   	engineid=$(echo $data | xxd -r -p | od -Ax -tx1 | text2pcap -q -6 $src,2001:db8::1 -T 12345,161 -t "%F %T." - - | tshark -r - -T fields -e snmp.msgAuthoritativeEngineID)
   	echo "$src,$engineid" >> repro_folder/targets_with_engineid.csv
   done < <(cut -d "," -f 1,12 2023-09-28-udp161-snmpv3_filtered.csv | grep ":")
   ```

4. Follow the next step in the **Jupyter Notebook to convert the engineID to a vendor label.**

   The SNMP Engine ID is always twelve octets in length. The first four octets identify an enterprise. E.g.: Cisco is '9', IBM is '2'.

   The mapping is publicly available [IANA Engine IDS](https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers).

   The remaining eight octets are left for the enterprise to specify. The fifth octet specifies the format scheme, which then specifies the information included in the remainder of the SNMP Engine ID (1=IPv4,2=IPv6, 3=MAC, 4=Text, 5=Octets). If the format is 03 -> Extract the MAC Address -> Extract vendor from MAC. 

   >  [!IMPORTANT] 
   >
   >  Why do we prefer MAC over enterprise IDs? Enterprise ID could be cisco, but cisco could run routers from other vendors inside its own network => MAC vendor is more accurate than enterprise ID

##### 2.3.2 Vendor Label Matching 🔎 (see Jupyter Notebook)

To match collected TX error rates against the collected router defaults, we store the recorded ICMPv6 error message rates in the following format:

>  Timelines: Including a 1d vector binning the number error messages per second
>
> BS (Bucket Size): The number of initial responses until a refill if initial_time < refill_interval, else we substract the refilled responses from the bucket size
>
> RI (Refill Interval in milliseconds): Adaptive round on the median of inter burst times. The inter burst time is the time span between the first responses of a refill until the time of the first response of the next refill.
>
> RS (Refill Size): Median of the tokens that get refilled after the bucket is depleted. Excluding the interval before the bucket is depleted for the first time.

```
"Huawei": {
		"ratelimit1":{
			"TYP":"lab",
			"TAG":"NE40",
			"NR10":"1000-1100",
			"timelines":["100-200,100,100,100,100,100,100,100,100,100"],
			"BS":"100-200",
			"RI":1000,
			"RS":100
		},
```

`Path: data/data_ratelimits/rates.json`

The matching occurs in a three step approach:

1) Select candidate error rates that are within a certain distance treshhold of the timeline vector. (Adaptive threshold from 10 to 100 based on number of packets)
2) Within these timelines, match rate limiting parameters BS - Bucket Size, RI - Refill Intervall & RS - Refill Size.
3) From these fingerprints the one with the lowest distance to the timeline vector is chosen.



## 📡 Measurements

In addition to our code, we publish measurement scripts (written in bash) to conduct measurements on your own. 

To collect error messages and rate limits in the IPv6 Internet we rely on the [1. TU Munich ZMap](https://github.com/tumi8/zmap), and 2. customized versions of ZMap to include a request number, parallel ZMap execution, these versions are included in `Path: measurements/zmap_versions`

Each measurement folder includes a `scan.conf` including a subset of the following parameters

> [!IMPORTANT]
>
> ip=<public ipv6 source address for scanning> # `ip a`; Additionally before scanning for good Internet citizenship, set a reverse dns entry on that IP explaining the reason why you perform this scan  <string>
> mac=<mac address of the interface> # again `ip a`, it includes the mac address of the interface   <string>
> gw=<mac address of the gateway> # use `ip - 6 neigh`  <string>
> int=<name of source interface> #use the interface name <string>
> speed=<200,1000,...> # The number of packets per second <integer>
> proto=<all, icmp, tcp or udp> #the protocol to perform scans with <string>
> outdir= <output directory> # folder to store scan results <string>
> zmap=<path to zmap version>  <string>
> yarrp=<optional: path to yarrp binary> <string>

Each measurement folder includes a .sh (bash) script to orchestrate the measurements.

We performed Internet measurements for:

- Response Types and Codes:
  - BValues: `measurements/types_and_codes/bvalues`
  - Network Activity Scans `measurements/types_and_codes/network_activity_scans`
- Rate Limits
  - Routerscan `measurements/ratelimits/routerscan`

We performed local measurements for:

- Response Types and Codes:
  - Router Defaults:  [router lab](https://github.com/sbaresearch/router-lab)
- Rate Limits:
  - Kernels: `measurements/ratelimits/kerneldefaults`
  - Router Defaults:  `measurements/ratelimits/routerlab`
    - `./orchestrate_nd_rate_limits_single_destination.sh 1 0c:62:29:65:00:00 all paper 200 10`
