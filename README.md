# Site File Generator
This tool was created during an internship, it takes an input file containg a list of salt masters and Chassis Management Controllers (CMCs) and generates an output containing an inventory of all reachable salt minions.

## Information sources
Most information is obtained directly from the salt masters, however specific information (e.g. drive information, dimm info, raid controllers etc) is obtained by querying the iDRACs via SNMP.

## How the iDRAC IPs are found
The iDRAC IPs are obtained by SSHing into the CMCs and querying them for the iDRAC IPs of certain servers (specified by service tag).

### All scraping and querying is done in parallel using multiple threads
