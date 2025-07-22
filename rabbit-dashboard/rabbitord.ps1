# Set credentials
$User = "monitor"
$Password = "monitor"
$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential ($User, $SecurePassword)

# Define URLs
$urls = @(
    "https://rabbitmq-01.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-03.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-04.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-05.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-06.prod.ord.us.oracle.careaware.net/api/overview"
)

foreach ($url in $urls) {
    $baseUrl = $url -replace "/api/overview$", ""
    $queuesUrl = "$baseUrl/api/queues"

    try {
        $overview = Invoke-RestMethod -Uri $url -Credential $Cred -Method Get -UseBasicParsing -SkipCertificateCheck
        $queues = Invoke-RestMethod -Uri $queuesUrl -Credential $Cred -Method Get -UseBasicParsing -SkipCertificateCheck

        if ($queues.Count -gt 0) {
            $topQueues = $queues | Sort-Object { $_."messages_ready" } -Descending | Select-Object -First 3
            Write-Host "`nCluster: $($overview.cluster_name)"
