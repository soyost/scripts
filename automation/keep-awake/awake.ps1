param(
    [ValidateRange(0, 525600)]
    [int]$Minutes = 0,

    [switch]$KeepDisplayOn
)

$ErrorActionPreference = 'Stop'

# Add the C# type only if it has not already been loaded
if (-not ('PowerState' -as [type])) {
    Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class PowerState
{
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
}

# Use decimal values to avoid PowerShell's signed hexadecimal parsing
[uint32]$ES_CONTINUOUS       = 2147483648
[uint32]$ES_SYSTEM_REQUIRED  = 1
[uint32]$ES_DISPLAY_REQUIRED = 2

[uint32]$flags = $ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED

if ($KeepDisplayOn) {
    $flags = $flags -bor $ES_DISPLAY_REQUIRED
}

try {
    $result = [PowerState]::SetThreadExecutionState($flags)

    if ($result -eq 0) {
        throw "Windows rejected the request to prevent sleep."
    }

    if ($Minutes -gt 0) {
        Write-Host "Keeping Windows awake for $Minutes minute(s)."
        Write-Host "Press Ctrl+C to stop early."

        Start-Sleep -Seconds ($Minutes * 60)
    }
    else {
        Write-Host "Keeping Windows awake indefinitely."
        Write-Host "Press Ctrl+C to stop."

        while ($true) {
            Start-Sleep -Seconds 60
        }
    }
}
finally {
    [PowerState]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
    Write-Host "`nNormal sleep behavior restored."
}