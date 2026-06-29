param(
  [Parameter(Mandatory=$true)][string]$Merkle,
  [Parameter(Mandatory=$true)][uint32]$Time,
  [Parameter(Mandatory=$true)][uint32]$Bits,
  [int]$Version = 4,
  [uint32]$Start = 0,
  [uint32]$Stride = 1,
  [int]$ReportEvery = 10000000,
  [string]$Out = ".\found.json"
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Security

function HexToBytes([string]$hex){
  $hex=$hex.Replace('0x','').Replace(' ',''); if($hex.Length%2){throw "odd hex len"}
  $b=New-Object byte[] ($hex.Length/2)
  for($i=0;$i -lt $b.Length;$i++){$b[$i]=[Convert]::ToByte($hex.Substring(2*$i,2),16)}
  return $b
}
function U32LE([uint32]$u){ [BitConverter]::GetBytes($u) }
function Hash256([byte[]]$buf){ $sha=[System.Security.Cryptography.SHA256]::Create(); $sha.ComputeHash($sha.ComputeHash($buf)) }
function LEtoBE([byte[]]$h){ $x=[byte[]]$h.Clone(); [Array]::Reverse($x); $x }

# Header invarianti
$verLE  = U32LE([uint32]$Version)
$prev32 = New-Object byte[] 32
$merkleBE = HexToBytes $Merkle
$merkleLE = [byte[]]$merkleBE.Clone(); [Array]::Reverse($merkleLE)
$timeLE = U32LE $Time
$bitsLE = U32LE $Bits

# Target da nBits (big-endian 32)
$exp=[int]($Bits -shr 24); $mant=$Bits -band 0x00FFFFFF
$target = New-Object byte[] 32
$target[$exp-3] = [byte](($mant -shr 16) -band 0xFF)
$target[$exp-2] = [byte](($mant -shr  8) -band 0xFF)
$target[$exp-1] = [byte]($mant -band 0xFF)

# Header buffer
$H = New-Object byte[] 80
[Array]::Copy($verLE, 0, $H, 0, 4)
# prevhash zero
[Array]::Copy($merkleLE, 0, $H, 36, 32)
[Array]::Copy($timeLE,  0, $H, 68, 4)
[Array]::Copy($bitsLE,  0, $H, 72, 4)

$sw=[Diagnostics.Stopwatch]::StartNew()
$nonce=[uint32]$Start
$tries=0

while($true){
  if(Test-Path $Out){ break }  # qualcuno ha già trovato
  [Array]::Copy((U32LE $nonce),0,$H,76,4)
  $le=Hash256 $H; $be=LEtoBE $le
  # be <= target
  $cmp=0; for($i=0;$i -lt 32 -and $cmp -eq 0;$i++){ $cmp = $be[$i]-$target[$i] }
  if($cmp -le 0){
    $hash = ($be | % { '{0:x2}' -f $_ }) -join ''
    [pscustomobject]@{
      merkle=$Merkle.ToLower(); time=$Time; bits=('{0:X8}' -f $Bits)
      version=$Version; nonce=[int64]$nonce; hash_be=$hash
      mh_s=[math]::Round(($tries/[math]::Max(1,$sw.Elapsed.TotalSeconds))/1e6,2)
    } | ConvertTo-Json | Set-Content -Encoding UTF8 $Out
    break
  }
  $tries++
  $nonce=[uint32]($nonce+$Stride)
  if(($tries % $ReportEvery) -eq 0){
    $rate=[math]::Round(($tries/$sw.Elapsed.TotalSeconds)/1e6,2)
    Write-Host ("[{0}] ... scanned {1}M @ {2} MH/s  lastNonce={3}" -f $Start, [math]::Round($tries/1e6,2), $rate, $nonce)
  }
}
