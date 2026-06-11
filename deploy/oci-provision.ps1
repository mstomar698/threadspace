# Provision ThreadSpace networking + A1 VM on Oracle Cloud (OCI CLI).
#
# Prerequisites:
#   - OCI CLI installed and authenticated (oci session authenticate)
#   - SSH public key at ~/.ssh/threadspace_deploy.pub
#
# Usage:
#   1. Set $TenancyOcid below (or pass -TenancyOcid on the command line).
#   2. powershell -ExecutionPolicy Bypass -File deploy/oci-provision.ps1
#
# If you get "Out of host capacity", see docs/ORACLE_DEPLOY.md Part 5.

param(
    [string]$TenancyOcid = "",
    [int]$Ocpus = 1,
    [int]$MemoryGB = 6,
    [string]$Region = "ap-mumbai-1"
)

$ErrorActionPreference = "Stop"
$env:OCI_CLI_AUTH = "security_token"
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "True"

$oci = "oci"
if (Get-Command oci -ErrorAction SilentlyContinue) { $oci = "oci" }
elseif (Test-Path "$env:USERPROFILE\bin\oci.exe") { $oci = "$env:USERPROFILE\bin\oci.exe" }

if (-not $TenancyOcid) {
    $cfg = "$env:USERPROFILE\.oci\config"
    if (Test-Path $cfg) {
        $TenancyOcid = (Get-Content $cfg | Where-Object { $_ -match '^tenancy=' }) -replace '^tenancy=', ''
    }
}
if (-not $TenancyOcid) {
    Write-Error "Set -TenancyOcid or add tenancy= to ~/.oci/config"
}

$keyPub = "$env:USERPROFILE\.ssh\threadspace_deploy.pub"
if (-not (Test-Path $keyPub)) {
    Write-Error "Missing $keyPub — run: ssh-keygen -t ed25519 -f `$HOME\.ssh\threadspace_deploy -N '""'"
}

$ad = (& $oci iam availability-domain list --compartment-id $TenancyOcid --output json | ConvertFrom-Json).data[0].name
$img = (& $oci compute image list --compartment-id $TenancyOcid --operating-system "Canonical Ubuntu" `
    --operating-system-version "24.04" --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC `
    --query 'data[0].id' --raw-output)
$tmp = ($env:TEMP -replace '\\', '/')

Write-Host "Tenancy: $TenancyOcid"
Write-Host "AD:      $ad"
Write-Host "Image:   $img"
Write-Host "Shape:   $Ocpus OCPU / ${MemoryGB} GB"

# VCN
Set-Content "$env:TEMP\ts-cidr.json" '["10.0.0.0/16"]' -Encoding ascii
$vcn = (& $oci network vcn create --compartment-id $TenancyOcid --cidr-blocks "file://$tmp/ts-cidr.json" `
    --display-name threadspace-vcn --dns-label tsvcn | ConvertFrom-Json).data
$vcnId = $vcn.id
$rtId  = $vcn.'default-route-table-id'
$slId  = $vcn.'default-security-list-id'

# Internet gateway + route
$ig = (& $oci network internet-gateway create --compartment-id $TenancyOcid --vcn-id $vcnId `
    --is-enabled true --display-name threadspace-ig | ConvertFrom-Json).data
Set-Content "$env:TEMP\ts-route.json" "[{""destination"":""0.0.0.0/0"",""destinationType"":""CIDR_BLOCK"",""networkEntityId"":""$($ig.id)""}]" -Encoding ascii
& $oci network route-table update --rt-id $rtId --route-rules "file://$tmp/ts-route.json" --force | Out-Null

# Security list: 22, 80, 443
$ingress = @'
[
 {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
 {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
 {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":443,"max":443}}}
]
'@
Set-Content "$env:TEMP\ts-ingress.json" $ingress -Encoding ascii
& $oci network security-list update --security-list-id $slId --ingress-security-rules "file://$tmp/ts-ingress.json" --force | Out-Null

# Subnet
$subnet = (& $oci network subnet create --compartment-id $TenancyOcid --vcn-id $vcnId --cidr-block 10.0.1.0/24 `
    --display-name threadspace-subnet --dns-label tssub | ConvertFrom-Json).data
$subnetId = $subnet.id

# Launch (may fail with "Out of host capacity" — retry later)
Set-Content "$env:TEMP\ts-shape.json" "{`"ocpus`":$Ocpus,`"memoryInGBs`":$MemoryGB}" -Encoding ascii
Write-Host "Launching instance..."
$inst = (& $oci compute instance launch --compartment-id $TenancyOcid --availability-domain $ad `
    --shape VM.Standard.A1.Flex --shape-config "file://$tmp/ts-shape.json" --image-id $img `
    --subnet-id $subnetId --assign-public-ip true --display-name threadspace `
    --ssh-authorized-keys-file $keyPub --wait-for-state RUNNING | ConvertFrom-Json).data

$vnics = (& $oci compute instance list-vnics --instance-id $inst.id | ConvertFrom-Json).data
Write-Host ""
Write-Host "INSTANCE_OCID = $($inst.id)"
Write-Host "PUBLIC_IP     = $($vnics[0].'public-ip')"
Write-Host ""
Write-Host "Next: docs/ORACLE_DEPLOY.md Part 6 (VM bootstrap) then DEPLOY.md"
