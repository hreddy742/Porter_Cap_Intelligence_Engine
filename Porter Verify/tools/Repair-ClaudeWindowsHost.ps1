$ErrorActionPreference = 'Continue'

$logPath = Join-Path $PSScriptRoot 'Repair-ClaudeWindowsHost.log'
$statusPath = Join-Path $PSScriptRoot 'Repair-ClaudeWindowsHost.status.txt'

"Started: $(Get-Date -Format o)" | Set-Content -LiteralPath $logPath

& DISM.exe /Online /Cleanup-Image /RestoreHealth 2>&1 |
    Tee-Object -FilePath $logPath -Append
$dismExit = $LASTEXITCODE

& sfc.exe /scannow 2>&1 |
    Tee-Object -FilePath $logPath -Append
$sfcExit = $LASTEXITCODE

@(
    "Completed: $(Get-Date -Format o)"
    "DISM exit code: $dismExit"
    "SFC exit code: $sfcExit"
) | Set-Content -LiteralPath $statusPath

exit ([Math]::Max($dismExit, $sfcExit))
