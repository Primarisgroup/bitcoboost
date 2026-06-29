param([switch]$Mine)
$ErrorActionPreference = "Stop"

$cli    = 'D:\bitcoboost\src\bitcoin-cli.exe'
$dd     = 'D:\bitcoboost\bb_main_boost7'
$rpc    = 38211
$wallet = 'bb_wallet'

# Helper: esegue bitcoin-cli e converte l'output JSON
function J {
  param([string[]]$Cmd)
  (& $cli "-datadir=$dd" "-rpcport=$rpc" @Cmd 2>$null) | ConvertFrom-Json
}

Write-Host "=== BitcoBoost QuickCheck ==="

# Height
$h = & $cli "-datadir=$dd" "-rpcport=$rpc" getblockcount
Write-Host ("Height         : {0}" -f $h)

# Deployments (con fallback)
try {
  $dep = J @('getdeploymentinfo')
  $b34 = $dep.deployments.bip34.active
  $b65 = $dep.deployments.bip65.active
  $b66 = $dep.deployments.bip66.active
  $tap = $dep.deployments.taproot.bip9.status
  Write-Host ("BIP34/65/66   : {0}/{1}/{2}" -f $b34,$b65,$b66)
  Write-Host ("Taproot BIP9  : {0}" -f $tap)
} catch {
  Write-Host "Deployment info: n/a"
}

# Wallets
$wl = (& $cli "-datadir=$dd" "-rpcport=$rpc" listwallets | ConvertFrom-Json)
Write-Host ("Wallets       : {0}" -f ($wl -join ', '))

# Bilanci
try {
  $bal = & $cli "-datadir=$dd" "-rpcport=$rpc" "-rpcwallet=$wallet" getbalances | ConvertFrom-Json
  $t  = '{0:N8}' -f $bal.mine.trusted
  $im = '{0:N8}' -f $bal.mine.immature
  Write-Host ("Balance(trust): {0} | Immature: {1}" -f $t, $im)
} catch {
  Write-Host "Nota: wallet '$wallet' non caricato o assente."
}

# Mining opzionale
if ($Mine) {
  Write-Host "[mine] 1 blocco…"
  powershell -ExecutionPolicy Bypass -File D:\bitcoboost\tools\bb-mine.ps1 -N 1 | Write-Host
  $h2 = & $cli "-datadir=$dd" "-rpcport=$rpc" getblockcount
  Write-Host ("Height now    : {0}" -f $h2)
}

Write-Host "=== OK ==="
