## PURPOSE
Automating saving running-configuration for multiple Cisco switches, both IOS and NXOS
### USAGE
### IOS
1. Create and poplulate the respective ios-inventory.txt with the hosts that are targeted
1. Run
```bash
python copy-run-star-ios.py 
```
1. Script will prompt for TACACS/ssh credentials
1. Output is written to ios_results.csv with the following headers:
```bash
host,status,timestamp,device_hostname,device_clock,proof,error
```
### NXOS
1. Create and poplulate the respective nxos-inventory.txt with the hosts that are targeted
1. Run
```bash
python copy-run-star-ios.py 
```
1. Script will prompt for TACACS/ssh credentials
1. Output is written to nxos_results.csv with the following headers:
```bash
host,status,timestamp,device_hostname,device_clock,proof,error
```