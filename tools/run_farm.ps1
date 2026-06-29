param(
  [string]$Exe        = "D:\bitcoboost-mirror\tools\GenesisMiner.exe",
  [string]$Merkle     = "f1f855c804e50fd723eef2bbbb577c41f8cc172ce15e97096cde3cc00bbfc747",
  [string]$Bits       = "1e0ffff0",
  [int]$ThreadsPerProc = 1,
  [int]$BaseTime      = 1762086000,
  [int]$Workers       = 16
)

$ErrorActionPreference = 'Stop'
$logs = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (Test-Path $logs) { Remove-Item -Recurse -Force $logs }
New-Item -ItemType Directory -Path $logs | Out-Null

$procs = @()
for ($i = 0; $i -lt $Workers; $i++) {
    $t   = $BaseTime + $i
    $log = Join-Path $logs ("w{0}.log" -f $i)
    $args = "--merkle $Merkle --time $t --bits $Bits --version 4 --threads $ThreadsPerProc --start $i --stride $Workers"
    Write-Host "Avvio worker $i @ time=$t  -> $log"
    $p = Start-Process -FilePath $Exe -ArgumentList $args -RedirectStandardOutput $log -NoNewWindow -PassThru
    $procs += $p
}

# Poll ogni 5s: quando un log contiene 'FOUND', mostra il risultato e ferma gli altri
$winner = $null
while (-not $winner) {
    Start-Sleep -Seconds 5
    Get-ChildItem -Path $logs -Filter *.log | ForEach-Object {
        $tail = Get-Content -LiteralPath $_.FullName -Tail 5 -ErrorAction SilentlyContinue
        if ($tail -match '^(?i)FOUND\s') { $winner = $_.FullName }
    }
}

Write-Host "`n✅ TROVATO in: $winner" -ForegroundColor Green
Get-Content -LiteralPath $winner -Tail 50

# Stop altri worker
$procs | ForEach-Object { try { $_.Kill() } catch {} }
