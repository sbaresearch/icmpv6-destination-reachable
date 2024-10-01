#!/bin/bash

# Permission handling for capturing
ZMAP=<path to zmap>
setcap cap_net_raw=eip ${ZMAP}


