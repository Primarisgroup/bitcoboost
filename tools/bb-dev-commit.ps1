param(
  [string]$RepoPath = "D:\bitcoboost",
  [string[]]$Add = @("run_two_nodes.cmd","stop_two_nodes.cmd","tools\bb-smoketest-regtest.ps1"),
  [string]$Message = "tools: regtest two-node demo passing (A→B tx + sync)",
  [string]$Tag = "v27.1.0-bb13-regtest-demo",
  [string]$TagMessage = "Regtest demo OK",
  [ValidateSet("Global","Local")] [string]$IdentityScope = "Global",
  [string]$UserName = "Massimiliano",
  [string]$UserEmail = "massimiliano22@hotmail.it",
  [switch]$Push
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
  & git -C $RepoPath @Args
}

function Invoke-Git2 {
  param(
    [Parameter(Mandatory,Position=0)][string]$Cmd,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Args
  )
  & git -C $RepoPath $Cmd @Args
}

# 0) Verifica repo
if (-not (Test-Path (Join-Path $RepoPath ".git"))) { throw "Non sembra una repo Git: $RepoPath" }

# 1) safe.directory per D:/... e /d/...
$pathsToAllow = @(
  ($RepoPath -replace "\\","/"),
  ("/{0}/{1}" -f ($RepoPath.Substring(0,1).ToLower()), ($RepoPath.Substring(3) -replace "\\","/"))
) | Select-Object -Unique

$currentSafe = @()
try { $currentSafe = (git config --global --get-all safe.directory 2>$null) } catch {}
foreach($p in $pathsToAllow){
  if (-not $currentSafe -or -not ($currentSafe -contains $p)) {
    git config --global --add safe.directory $p | Out-Null
  }
}

# 2) Identità Git (globale o locale)
if ($IdentityScope -eq "Global") {
  $curName  = $null; $curEmail = $null
  try { $curName  = (git config --global user.name  2>$null) } catch {}
  try { $curEmail = (git config --global user.email 2>$null) } catch {}
  if (-not $curName)  { git config --global user.name  $UserName  | Out-Null }
  if (-not $curEmail) { git config --global user.email $UserEmail | Out-Null }
} else {
  $curName  = $null; $curEmail = $null
  try { $curName  = (Invoke-Git2 config user.name  2>$null) } catch {}
  try { $curEmail = (Invoke-Git2 config user.email 2>$null) } catch {}
  if (-not $curName)  { Invoke-Git2 config user.name  $UserName  | Out-Null }
  if (-not $curEmail) { Invoke-Git2 config user.email $UserEmail | Out-Null }
}

# 3) Add → Commit (solo se ci sono file nello staging)
$AddNorm = $Add | ForEach-Object { $_ -replace '\\','/' }
Invoke-Git add -- $AddNorm

# Guarda SOLO lo staging
$dirty = (Invoke-Git diff --cached --name-only | Out-String).Trim()
if ($dirty) {
  Invoke-Git commit -m $Message
} else {
  Write-Host "Nessuna modifica nello staging — skip commit."
}

# 4) Tag (idempotente)
if ($Tag) {
  $exists = [string](Invoke-Git tag -l $Tag 2>$null)
  if ($exists) { Write-Host "Tag '$Tag' esiste già — skip." }
  else { Invoke-Git tag -a $Tag -m $TagMessage }
}

# 5) Push opzionale
if ($Push) {
  $remotes = (Invoke-Git remote).Trim()
  if ($remotes) { Invoke-Git push --follow-tags }
  else { Write-Host "Nessun remote configurato — skip push." }
}

# 6) Riepilogo
"`n=== ULTIMO COMMIT ==="
Invoke-Git log -1 --decorate --name-only
"`n=== ULTIMI TAG ==="
Invoke-Git tag -n | Select-Object -Last 5



