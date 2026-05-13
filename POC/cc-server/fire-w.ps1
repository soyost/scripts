New-NetFirewallRule -DisplayName "CC TCP 5000" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 5000 `
  -Action Allow

New-NetFirewallRule -DisplayName "CC WEB 8080" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8080 `
  -Action Allow