## Purpose
This script is to generate a topology for a given switch. By leveraging lldp neighbors and interface status, the script will gather uplinks, connected interfaces, respective vlans, etc.

## Usage

```bash
python switch_mapper.py
```

Example:

```bash
Switch hostname or IP: Switchname
Username: user
Password: 
Connected to Switchname
Collecting LLDP neighbors...
Collecting interface status...
Wrote mapping\Switchname.html
Wrote mapping\Switchname.csv
```

* Rendering will open in browser

Example:

<img src="../images/switch-map-1.png" width="800" alt="Rendering In Browser">
