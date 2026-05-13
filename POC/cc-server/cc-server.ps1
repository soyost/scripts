$shared = [hashtable]::Synchronized(@{})
$shared.CaptionBuffer = @("Waiting for captions...")

#
# TCP LISTENER
#

$tcpScript = {

    param($shared)

    $tcpListener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Any,
        5000
    )

    $tcpListener.Start()

    while ($true) {

        $client = $tcpListener.AcceptTcpClient()

        $shared.CaptionBuffer = @("CC device connected...")

        $stream = $client.GetStream()
        $buffer = New-Object byte[] 4096

        while (($bytesRead = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {

            $text = [System.Text.Encoding]::UTF8.GetString(
                $buffer,
                0,
                $bytesRead
            )

            #
            # CLEANUP / PARSING
            #

            # Remove non-printable characters
            $text = $text -replace '[^\x20-\x7E\r\n]', ''
            
            # Keep the censor
            $text = $text -replace '#\(','*'

            # Music marker FIRST
            $text = $text -replace '&-p7', ' ♪ '

            # Remove paragraph/page markers
            $text = $text -replace '&-p\d*', ' '

            # Remove leftover standalone 3 markers
            $text = $text -replace '\b3\b', ''

            # Normalize spacing
            $text = $text -replace '\s+', ' '


            # Trim edges
            $text = $text.Trim()

            #
            # BUFFERING
            #

            if ($text.Length -gt 0) {

                if ($shared.CaptionBuffer.Count -eq 0) {

                    $shared.CaptionBuffer += $text
                }
                else {

                    $last = $shared.CaptionBuffer[-1]

                    $combined = ($last + " " + $text).Trim()

                    # Tune this number for line length
                    if ($combined.Length -lt 70) {

                        $shared.CaptionBuffer[-1] = $combined
                    }
                    else {

                        $shared.CaptionBuffer += $text
                    }
                }

                # Keep only latest 4 lines
                if ($shared.CaptionBuffer.Count -gt 10) {

                    $shared.CaptionBuffer =
                        $shared.CaptionBuffer[-10..-1]
                }
            }
        }

        $shared.CaptionBuffer += "CC device disconnected"

        if ($shared.CaptionBuffer.Count -gt 10) {

            $shared.CaptionBuffer =
                $shared.CaptionBuffer[-10..-1]
        }

        $client.Close()
    }
}

#
# START TCP THREAD
#

$ps = [powershell]::Create()

$ps.AddScript($tcpScript).AddArgument($shared) | Out-Null

$ps.BeginInvoke() | Out-Null

#
# WEB SERVER
#

$listener = New-Object System.Net.HttpListener

$listener.Prefixes.Add("http://+:8080/")

$listener.Start()

Write-Host "TCP listener started on port 5000"
Write-Host "Web server started on port 8080"

#
# HTML PAGE
#

$html = @"
<!doctype html>
<html>

<head>

<title>Closed Captions</title>

<style>

body {
    background: black;
    color: white;
    font-size: 28px;
    font-family: Arial;
    padding: 20px;
    overflow-x: hidden;
}

#caption {
    white-space: pre-wrap;
    overflow-wrap: break-word;
    line-height: 1.3;
}

</style>

</head>

<body>

<div id="caption">Waiting for captions...</div>

<script>

async function updateCaption() {

    let response = await fetch('/caption?t=' + Date.now());

    let text = await response.text();

    document.getElementById('caption').innerText = text;
}

setInterval(updateCaption, 300);

updateCaption();

</script>

</body>

</html>
"@

#
# HTTP LOOP
#

while ($listener.IsListening) {

    $context = $listener.GetContext()

    $request = $context.Request

    $response = $context.Response

    if ($request.Url.AbsolutePath -eq "/caption") {

        $content = ($shared.CaptionBuffer -join "`r`n")

        $response.ContentType = "text/plain"
    }
    else {

        $content = $html

        $response.ContentType = "text/html"
    }

    $buffer = [System.Text.Encoding]::UTF8.GetBytes($content)

    $response.ContentLength64 = $buffer.Length

    $response.OutputStream.Write($buffer, 0, $buffer.Length)

    $response.OutputStream.Close()
}