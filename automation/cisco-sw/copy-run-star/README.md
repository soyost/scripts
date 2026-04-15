## USAGE
1. Create and poplulate inventory.txt with the hosts that are targeted
1. Run
```bash
python copy-run-star.py 
```
1. Script will prompt for TACACS/ssh credentials
1. Output is written to save_results.csv with the following headers:
```bash
host,status,timestamp,device_hostname,device_clock,proof,error
```
