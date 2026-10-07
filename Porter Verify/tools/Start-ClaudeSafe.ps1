$ErrorActionPreference = "Stop"

function Show-ClaudeMessage([string]$message) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        $message,
        "Claude Safe Mode",
        [System.Windows.MessageBoxButton]::OK,
        [System.Windows.MessageBoxImage]::Information
    ) | Out-Null
}

$package = Get-AppxPackage -Name Claude -ErrorAction SilentlyContinue
if ($null -eq $package) {
    Show-ClaudeMessage "Claude is not installed. Reinstall Claude before using Safe Mode."
    exit 1
}

$mainProcess = Get-CimInstance Win32_Process -Filter "Name='claude.exe'" |
    Where-Object { $_.CommandLine -notmatch "--type=" } |
    Select-Object -First 1

if ($null -ne $mainProcess) {
    $safeFlagsPresent =
        $mainProcess.CommandLine -match "--disable-gpu" -and
        $mainProcess.CommandLine -match "--disable-software-rasterizer" -and
        $mainProcess.CommandLine -match "--disable-gpu-compositing"

    if (-not $safeFlagsPresent) {
        Show-ClaudeMessage "Claude is already running without Safe Mode. Use File > Exit in Claude, then open the Claude Safe Mode shortcut again."
        exit 2
    }

    exit 0
}

$eccDisableLocations = @(
    "C:\Users\hreddy\.claude\homunculus\disabled",
    "C:\Users\hreddy\.local\share\ecc-homunculus\disabled"
)

foreach ($marker in $eccDisableLocations) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $marker) -Force | Out-Null
    New-Item -ItemType File -Path $marker -Force | Out-Null
}

$claudeExe = Join-Path $package.InstallLocation "app\Claude.exe"
Start-Process -FilePath $claudeExe -ArgumentList @(
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-gpu-compositing"
)
