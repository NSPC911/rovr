if (-not $IsWindows) {
    Write-Host "Bro."
    return
}

$installPath = Join-Path $env:LOCALAPPDATA "Programs\rovr"
if (-not (Test-Path $installPath)) {
    Write-Host "rovr is not installed at $installPath."
    return
}

$exe = Get-Item (Join-Path $installPath "rovr.exe") -ErrorAction SilentlyContinue
if ($null -ne $exe) {
    $ver = "v" + (& $exe.FullName --version 2>$null).Split()[1]
    Write-Host "Found rovr $($PSStyle.Foreground.Cyan)$ver$($PSStyle.Reset) installed at $installPath."
}

$options = [System.Management.Automation.Host.ChoiceDescription[]]@(
    [System.Management.Automation.Host.ChoiceDescription]::new("&Yes", "Uninstall rovr"),
    [System.Management.Automation.Host.ChoiceDescription]::new("&No", "Keep rovr installed")
)
$result = $host.ui.PromptForChoice("Uninstall rovr", "Are you sure you want to uninstall rovr?", $options, 1)
if ($result -ne 0) {
    Write-Host "Uninstallation cancelled."
    return
}

Write-Host "Removing rovr from $installPath..."
Remove-Item $installPath -Recurse -Force

$envPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($envPath -like "*$installPath*") {
    Write-Host "Removing $installPath from PATH..."
    $newPath = ($envPath -split ";" | Where-Object { $_ -ne $installPath }) -join ";"
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

Write-Host "rovr has been uninstalled successfully."
