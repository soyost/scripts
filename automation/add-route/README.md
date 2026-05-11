## Usage
1. Inventory.txt with the target endpoints
2. ```bash
python add-route<site>.py
```
Checks only

1. ```bash
python add-route<site>.py --add
```
Adds route (nonpersistent)
1. ```bash
python add-route<site>.py --add --persistent
```
Adds route to .plist file and reloads