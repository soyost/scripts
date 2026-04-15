## USAGE
1. Poplulate inventory.txt with the target clients
1. Run
```bash
python catalyst-audit.py
```
1. You will be prompted for TACAS/ssh user and password
1. You will be asked for some vairables to tune the output
``bash
SSH username: <username>
SSH password: 
Include uptime? (y/n):
Include storage info (free space + staged images)? (y/n):
Include connected ports? (y/n):
1. Output will be documented in audit-results.csv with the following columns
```bash
host,os,chassis,current_os,uptime,free_space,staged_versions,connected_count,connected_interfaces
```
