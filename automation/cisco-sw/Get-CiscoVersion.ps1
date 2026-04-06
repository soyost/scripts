param(
    [Parameter(Mandatory=$true)][string]$Host,
    [Parameter(Mandatory=$true)][string]$User,
    [int]$Port = 22,
    [switch]$ShowRaw
)

# Compose a single remote command:
# - Force TTY with -tt so IOS accepts 'terminal length 0'
# - Chain commands with ';' so both run in the same session
$remoteCmd = 'terminal length 0 ; show version'

# Build SSH arguments
$sshArgs = @()
$sshArgs += '-tt'
$sshArgs += '-p'
$sshArgs += $Port
# Optionally relax host key prompts on first connect (uncomment if desired)
# $sshArgs += @('-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null')

# Run SSH and capture output
try {
    $output = & ssh @sshArgs "$User@$Host" $remoteCmd 2>&1
} catch {
    Write-Error "Failed to run ssh: $($_.Exception.Message)"
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "ssh exited with code $LASTEXITCODE. Output:`n$output"
    exit $LASTEXITCODE
}

if ($ShowRaw) {
    Write-Host "---- RAW OUTPUT START ----"
    $output | ForEach-Object { Write-Host $_ }
    Write-Host "---- RAW OUTPUT END ----"
}

# Parse version using common IOS/IOS-XE patterns:
#   Cisco IOS XE