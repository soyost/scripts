$User = "monitor"
$Password = "monitor"
$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential ($User, $SecurePassword)

# Define URLs
$urls = @(
    "https://rabbitmq-01.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.prod.ord.us.oracle.careaware.net/api/overview"
    # Add more as needed
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

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
            $topQueues = $queues | Sort-Object { ($_."messages_ready") } -Descending | Select-Object -First 3
            Write-Host "`nCluster: $($overview.cluster_name)"
            foreach ($q in $topQueues) {
                $totalMsgs = $q.messages_ready
                Write-Host "Queue: $($q.name) - Total Messages: $totalMsgs (Ready: $($q.messages_ready))"
            }
        } else {
            Write-Host "`nCluster: $($overview.cluster_name) - No queues found"
        }
    }
    catch {
        Write-Warning "Error retrieving data from $baseUrl - $_"
    }
}
