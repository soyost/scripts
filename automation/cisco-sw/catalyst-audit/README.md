## PURPOSE
This script will connect to the listed hosts to collect data or issue command(s) based on multiple variables.

1. Uptime.

2. Storage including installed SPA.bin files.

3. Interfaces showing connected status with port and description.

4. Issuing "copy run star"

4. Issuing scp to SFTP server for backup.


### USAGE
1. Poplulate inventory.txt with the target clients.

2. Run

```bash
python catalyst-audit.py
```

3. You will be prompted for TACAS/ssh user and password.

4. You will be asked for some variables to tune the output.

```bash
SSH username: <username>
SSH password: 
Include uptime? (y/n): 
Include storage info (free space + staged images)? (y/n): 
Include connected ports? (y/n): 
Copy running-config to startup-config? (y/n): 
Backup running-config to SCP? (y/n): 
```

5. Output will be documented in audit-results.csv with the following columns.

```bash
host,status,timestamp,os,chassis,current_os,uptime,free_space,staged_versions,save_status,save_proof,error
```
