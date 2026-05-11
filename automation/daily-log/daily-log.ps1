$logDir = "$env:USERPROFILE\Documents\Daily-Learning-Logs"
$date = Get-Date -Format "yyyy-MM-dd"
$logFile = "$logDir\$date.md"

if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

if (!(Test-Path $logFile)) {
    @"
# $date

## Learned

- 

## Things I did

- 

## Moved the needle

- 
"@ | Out-File -FilePath $logFile -Encoding utf8
}

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    "Take 5 minutes to log what you learned, did, or moved forward today.",
    "Daily Learning Log"
)

notepad.exe $logFile