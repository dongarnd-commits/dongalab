#Requires -RunAsAdministrator
<# UAT-only firewall rule. Does not edit the shared 8443 rule or Caddy.
   Run only after the user approves specific client addresses.
   Remove the owned rule with -Action Remove when acceptance ends. #>
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{12}$')][string]$Nonce,
    [ValidateSet('Allow','Remove')][string]$Action='Allow',
    [string[]]$RemoteAddress=@()
)
$ErrorActionPreference='Stop'
$repoRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime=(Resolve-Path -LiteralPath (Join-Path $repoRoot "storage/private/runtime/manual-acceptance/$Nonce")).Path
$manifest=Get-Content -LiteralPath (Join-Path $runtime 'manifest.json') -Raw -Encoding utf8 | ConvertFrom-Json
if($manifest.nonce -ne $Nonce -or $manifest.host -ne '10.10.10.145' -or $manifest.https_port -ne 8444) { throw 'UAT_FIREWALL_TARGET_REJECTED' }
$ruleName="DATCO-MVP-UAT-$Nonce"
$description="Owned synthetic manual acceptance $Nonce; TCP 8444 only; shared rule unchanged."
$existing=Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if($existing) {
    $port=$existing | Get-NetFirewallPortFilter
    $address=$existing | Get-NetFirewallAddressFilter
    $program=$existing | Get-NetFirewallApplicationFilter
    if($existing.Description -ne $description -or $port.LocalPort -ne '8444' -or
       $program.Program -ne $manifest.caddy -or [string]$address.LocalAddress -ne '10.10.10.145') { throw 'UAT_FIREWALL_OWNERSHIP_MISMATCH' }
}
if($Action -eq 'Remove') {
    if($existing) { Remove-NetFirewallRule -Name $ruleName }
    Write-Output 'UAT_FIREWALL_RULE_REMOVED_SHARED_RULE_UNCHANGED'
    exit 0
}
if(!$RemoteAddress.Count) { throw 'EXPLICIT_ACCEPTANCE_CLIENT_IP_REQUIRED' }
foreach($client in $RemoteAddress) {
    if($client -notmatch '^10\.10\.10\.(\d{1,3})$' -or [int]$Matches[1] -lt 1 -or [int]$Matches[1] -gt 254 -or $client -eq '10.10.10.145') { throw 'ONLY_EXPLICIT_LAN_CLIENT_IP_ALLOWED' }
}
if($existing) {
    if(@(Compare-Object @($address.RemoteAddress) @($RemoteAddress)).Count -gt 0) { throw 'EXISTING_UAT_SCOPE_DIFFERS_REVIEW_REQUIRED' }
    Write-Output 'UAT_FIREWALL_RULE_ALREADY_MATCHES'
    exit 0
}
New-NetFirewallRule -Name $ruleName -DisplayName "DATCO ONE MVP UAT $Nonce" -Description $description -Direction Inbound -Action Allow -Enabled True -Profile Private -Protocol TCP -LocalAddress '10.10.10.145' -LocalPort 8444 -RemoteAddress $RemoteAddress -Program $manifest.caddy | Out-Null
Write-Output 'UAT_FIREWALL_RULE_CREATED_SHARED_RULE_UNCHANGED'
