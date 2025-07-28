$User = "monitor"
$Password = "monitor"

$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential ($User, $SecurePassword)

# --- Force TLS 1.2 for HTTPS connections ---
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$urls = @(
    "https://rabbitmq-01.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-03.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-04.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-05.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-06.prod.ord.us.oracle.careaware.net/api/overview"
)

# Ignore SSL certificate errors
Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

foreach ($url in $urls) {
    $baseUrl = $url -replace "/api/overview$", ""
    $queuesUrl = "$baseUrl/api/queues"

    try {
        $overview = Invoke-RestMethod -Uri $url -Credential $Cred -Method Get -UseBasicParsing
        $queues = Invoke-RestMethod -Uri $queuesUrl -Credential $Cred -Method Get -UseBasicParsing

        if ($queues.Count -gt 0) {
            $topQueues = $queues | Sort-Object { $_.messages_ready } -Descending | Select-Object -First 3
            Write-Host "`nCluster: $($overview.cluster_name)"

            # <-- Replace your existing foreach with this fancy bar graph block -->
            foreach ($q in $topQueues) {
                $totalMsgs = $q.messages_ready
                $barLength = [math]::Min(50, [math]::Floor($totalMsgs / 10))
                $bar = '█' * $barLength
                $label = "{0} msgs" -f $totalMsgs

                Write-Host ("{0,-30} |{1,-50}| {2}" -f $q.name, $bar, $label)
            }
        } else {
            Write-Host "`nCluster: $($overview.cluster_name) - No queues found"
        }
    }
    catch {
        Write-Warning "Error retrieving data from $baseUrl - $_"
    }
}

Read-Host -Prompt "Press Enter to exit"
