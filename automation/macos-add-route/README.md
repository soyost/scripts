### Usage
Inventory.txt with the target endpoints

```bash
python add-route<site>.py
```

Checks only

```bash
python add-route<site>.py --add
```

Adds route (nonpersistent)

```bash
python add-route<site>.py --add --persistent
```

Adds route to .plist file and reloads

### Back-out
### OP

```bash
sudo route -n delete -net 10.10.10.10/24 10.10.10.10
sudo route -n delete -net 10.10.10.1/24 10.10.10.1
```

Remove Persistent
 ```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.company.evo-routes.plist
sudo rm -f /Library/LaunchDaemons/com.company.evo-routes.plist
sudo rm -f /usr/local/sbin/add-evo-routes.sh
```

* Project stalled. Saving script for reference