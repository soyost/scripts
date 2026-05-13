## USAGE
1. Save on

cc-server.ps1

1. Run

powershell.exe -ExecutionPolicy Bypass -File .\cc-server.ps1

1. Firewall policies need to be added

./fire-w.ps1

1. Open browser to

```bash
http://<IP>:8080
```

## Fine Tuning
1. Character length

```bash
($combined.Length -lt 70)
```

1. Line Length (two places)

```bash
if ($shared.CaptionBuffer.Count -gt 10) {

                    $shared.CaptionBuffer[-10..-1]
 ```
 
1. Web display

```bash
body {
    background: black;
    color: white;
    font-size: 28px;
    font-family: Arial;
    padding: 20px;
```
1. Refresh buffer time 

```bash
setInterval(updateCaption, 300);
```

