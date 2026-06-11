# Gentle retry for an A1 instance when networking already exists.
# Copy to your home dir or run from the repo. See docs/ORACLE_DEPLOY.md Part 5.
#
# Usage:
#   1. Set $SubnetOcid to your public subnet OCID.
#   2. powershell -ExecutionPolicy Bypass -File deploy/oci-launch-retry.ps1

param(
    [Parameter(Mandatory = $true)]
    [string]$SubnetOcid,
    [int]$Ocpus = 1,
    [int]$MemoryGB = 6,
    [int]$IntervalSec = 300
)

$ErrorActionPreference = "Stop"
$env:OCI_CLI_AUTH = "security_token"
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "True"

$oci = if (Test-Path "$env:USERPROFILE\bin\oci.exe") { "$env:USERPROFILE\bin\oci.exe" } else { "oci" }
$cfg = "$env:USERPROFILE\.oci\config"
$t = (Get-Content $cfg | Where-Object { $_ -match '^tenancy=' }) -replace '^tenancy=', ''
$ad = (& $oci iam availability-domain list --compartment-id $t | ConvertFrom-Json).data[0].name
$img = (& $oci compute image list --compartment-id $t --operating-system "Canonical Ubuntu" `
    --operating-system-version "24.04" --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC `
    --query 'data[0].id' --raw-output)
$keyPub = "$env:USERPROFILE\.ssh\threadspace_deploy.pub"
$tmp = ($env:TEMP -replace '\\', '/')
Set-Content "$env:TEMP\ts-shape.json" "{`"ocpus`":$Ocpus,`"memoryInGBs`":$MemoryGB}" -Encoding ascii

$fds = (& $oci iam fault-domain list --compartment-id $t --availability-domain $ad | ConvertFrom-Json).data.name
$i = 0
Write-Host "Retrying every $($IntervalSec/60) min. Ctrl+C to stop."

while ($true) {
    $fd = $fds[$i % $fds.Count]; $i++
    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $out = (& $oci compute instance launch --compartment-id $t --availability-domain $ad --fault-domain $fd `
        --shape VM.Standard.A1.Flex --shape-config "file://$tmp/ts-shape.json" --image-id $img `
        --subnet-id $SubnetOcid --assign-public-ip true --display-name threadspace `
        --ssh-authorized-keys-file $keyPub --wait-for-state RUNNING 2>&1 | Out-String)

    if ($LASTEXITCODE -eq 0) {
        $inst = ($out | ConvertFrom-Json).data
        $vnics = (& $oci compute instance list-vnics --instance-id $inst.id | ConvertFrom-Json).data
        Write-Host "PUBLIC_IP = $($vnics[0].'public-ip')"
        return
    }
    if ($out -match "Out of host capacity") { Write-Host "[$stamp] $fd : out of capacity" }
    elseif ($out -match "TooManyRequests") { Write-Host "[$stamp] $fd : rate limited"; Start-Sleep 600 }
    else { Write-Host "[$stamp] error:"; Write-Host $out }
    Start-Sleep -Seconds $IntervalSec
}
