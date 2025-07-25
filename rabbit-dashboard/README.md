## GUI INSTRUCTIONS
Pre-reqs: Python 3.10+ installed

Install required Python libraries: 
Run in terminal:

```bash
pip install requests plotly dash
```

Save the above Python script as rabbittop.py and rabbittopoke.py

## USAGE
Execute:

For Prod Clusters
```bash 
python3 rabbittop.py -p
```
For NonProd Clusters
```bash
python3 rabbittop.py -n
```
This will run in a terminal session while active. To quit the script, use Crtl + C in the terminal where you are running the script

Go to browser:

For TAS dashboard
```bash
http://127.0.0.1:8050
```
For OKE dashbpard
```bash
http://127.0.0.1:8051
```

## NOTES
Loads for the TAS dashbard are about 4 minutes, please be patient

You can keep it open in a browser tab alongside your usual work. You can hover over the bar graphs for actual totals. You can refresh the tab ad hoc. Top three queues are published and display by hovering over the bar graph. This tool auto refreshes every 30 minutes by default.


### Current PROD ORD PowerShell instructions

Copy rabbitord.ps1 somewhere on the shared box CERNCARUSDPY101

Create new shortcut (on desktop or somewhere else)

C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "LOCATION OF THE PS1 FILE"

Example
```bash
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\sy018616\Desktop\rabbit\rabbitord.ps1"
```

