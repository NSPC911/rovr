if (-not [Environment]::OSVersion.Platform -eq 'Win32NT') {
    Write-Host "As much as I want to support the 5 people that use Powershell on non-Windows system (myself included)"
    Write-Host "It is too much of a hastle to maintain. Instead, please use the alternative install.sh"
    return
}

if ($null -eq $ROVR_VERSION) {
    $ROVR_VERSION = (Invoke-RestMethod -Uri "https://api.github.com/repos/NSPC911/rovr/releases/latest").tag_name
}

try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/NSPC911/rovr/releases/tags/$ROVR_VERSION" -ErrorAction SilentlyContinue
} catch {
    Write-Error "Version $ROVR_VERSION does not exist."
    return
}

$installPath = Join-Path $env:LOCALAPPDATA "Programs\rovr"
if (-not $ROVR_FORCE_REINSTALL) {
    Write-Host "Checking for existing installation of rovr..."
    if (Test-Path $installPath) {
        $oldexe = Get-Item (Join-Path $installPath "rovr.exe") -ErrorAction SilentlyContinue
        if ($null -ne $oldexe) {
            $oldver = "v" + (& $oldexe.FullName --version 2>$null).Split()[1]
            if ($oldver -eq $ROVR_VERSION) {
                Write-Host "Specified version $($PSStyle.Foreground.Cyan)$ROVR_VERSION$($PSStyle.Reset) is already installed at $installPath."
                Write-Host "Skipping installation."
                return
            }
            if ($oldver -gt $ROVR_VERSION) {
                Write-Host "A newer version $($PSStyle.Foreground.Green)$oldver$($PSStyle.Reset) is already installed at $installPath."
                Write-Host "Are you sure you want to downgrade to $($PSStyle.Foreground.Cyan)$ROVR_VERSION$($PSStyle.Reset)? (y/N)"
                $options = [System.Management.Automation.Host.ChoiceDescription[]]@(
                    [System.Management.Automation.Host.ChoiceDescription]::new("&Yes", "Downgrade to $ROVR_VERSION"),
                    [System.Management.Automation.Host.ChoiceDescription]::new("&No", "Keep existing version $oldver")
                )
                $result = $host.ui.PromptForChoice("", "", $options, 1)
                if ($result -ne 0) {
                    Write-Host "Keeping existing version $($PSStyle.Foreground.Green)$oldver$($PSStyle.Reset)."
                    Write-Host "Skipping installation."
                    return
                }
            } else {
                Write-Host "An older version $($PSStyle.Foreground.Yellow)$oldver$($PSStyle.Reset) is already installed at $installPath."
                Write-Host "Updating to $($PSStyle.Foreground.Cyan)$ROVR_VERSION$($PSStyle.Reset)..."
                Remove-Item $installPath -Recurse -Force
            }
        }
    }
}

if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq [System.Runtime.InteropServices.Architecture]::Arm64)
{$arch = "arm"} else {$arch = "x64"}
Write-Host "Downloading rovr $ROVR_VERSION for Windows $arch..."

$downloadUrl = $release.assets | Where-Object { $_.name -eq "rovr-windows-$arch-nuitka.zip" } | Select-Object -ExpandProperty browser_download_url

$installPath = Join-Path $env:LOCALAPPDATA "Programs\rovr"
if (-Not (Test-Path $installPath)) {
    New-Item -ItemType Directory -Path $installPath | Out-Null
}
$zipPath = Join-Path $installPath "rovr.zip"
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath

Write-Host "Extracting zip..."
Expand-Archive -Path $zipPath -DestinationPath $installPath -Force
Remove-Item $zipPath

Write-Host "rovr $ROVR_VERSION has been installed to $installPath."
# set to env
# check for existing path
$envPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($envPath -notlike "*$installPath*") {
    Write-Host "Adding $installPath to system PATH..."
    $newPath = "$envPath;$installPath"
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    # also set it on the current session
    $env:Path += ";$installPath"
}
Write-Host "Installation complete. You can now run 'rovr' from any terminal."
Write-Host "Check out the the tutorial at https://nspc911.github.io/rovr/get-started/tutorial !"
