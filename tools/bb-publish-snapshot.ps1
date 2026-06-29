param(
  [string]$SourceDir  = 'D:\bitcoboost',
  [string]$PublishDir = 'D:\bb_publish2',
  [string]$Remote     = 'git@github.com:Maxtwin22/bitcoboost2.git',
  [string]$Branch     = 'phase2-branding',
  [string]$TagName,
  [string]$TagMessage,
  [switch]$OpenRelease
)

$ErrorActionPreference = 'Stop'

Write-Host "== Publish snapshot ==" -ForegroundColor Cyan
Write-Host ("Source  : {0}" -f $SourceDir)
Write-Host ("Publish : {0}" -f $PublishDir)
Write-Host ("Remote  : {0}" -f $Remote)
Write-Host ("Branch  : {0}" -f $Branch)
if ($TagName) { Write-Host ("Tag     : {0}" -f $TagName) }

# clean publish dir
if (Test-Path $PublishDir) { Remove-Item $PublishDir -Recurse -Force }
New-Item -ItemType Directory -Path $PublishDir | Out-Null

# copy (exclude .git and known big artifacts)
$rc = & robocopy $SourceDir $PublishDir /MIR /XD .git /XF `
  src\st3vWAeE src\st5xXL3l core_ucrt\src\stKNXoGD src\stLs9WWI
if ($LASTEXITCODE -gt 3) { throw "Robocopy failed (code $LASTEXITCODE)" }

# init publish repo (no EOL conversions to avoid warnings)
git -C $PublishDir init | Out-Null
git -C $PublishDir config core.autocrlf false
"* -text`r`n" | Set-Content -NoNewline (Join-Path $PublishDir '.gitattributes')

# branch reset
git -C $PublishDir checkout -B $Branch | Out-Null

# get source SHA for traceability
$srcSHA = (git -C $SourceDir rev-parse --short HEAD).Trim()

# commit snapshot
git -C $PublishDir add -A
$commitMsg = "Publish snapshot (no history) - branch $Branch`nfrom $srcSHA"
git -C $PublishDir commit -m $commitMsg | Out-Null

# push branch (force)
# Rimuovi 'origin' solo se esiste (evita errore)
$hasOrigin = (git -C $PublishDir remote 2>$null) -match '^origin$'
if ($hasOrigin) { git -C $PublishDir remote remove origin | Out-Null }

git -C $PublishDir remote add origin $Remote
git -C $PublishDir push -u -f origin $Branch

# optional tag with "from <SHA>" in message
if ($TagName) {
  if ($TagMessage) { $tagMsg = "$TagMessage`nfrom $srcSHA" } else { $tagMsg = "from $srcSHA" }
  git -C $PublishDir tag -f -a $TagName -m $tagMsg
  git -C $PublishDir push -f origin $TagName
}

# build ZIP (exclude .git) and compute SHA256
$headShort = (git -C $PublishDir rev-parse --short HEAD).Trim()
$repoName  = [IO.Path]::GetFileNameWithoutExtension( ($Remote -split '[:/]' | Select-Object -Last 1) )
if ([string]::IsNullOrWhiteSpace($repoName)) { $repoName = 'publish' }

$pkg = Join-Path $PublishDir '_pkg'
if (Test-Path $pkg) { Remove-Item $pkg -Recurse -Force }
New-Item -ItemType Directory -Path $pkg | Out-Null
& robocopy $PublishDir $pkg /MIR /XD .git | Out-Null

$zipName = "$repoName-$headShort-snapshot.zip"
$zipPath = Join-Path $PublishDir $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $pkg '*') -DestinationPath $zipPath -Force
$zipSha  = (Get-FileHash $zipPath -Algorithm SHA256).Hash

Write-Host "ZIP     : $zipPath"
Write-Host "SHA256  : $zipSha"

# alignment check
$localHead  = (git -C $PublishDir rev-parse HEAD).Trim()
$remoteHead = ((git -C $PublishDir ls-remote origin "refs/heads/$Branch") -split "`t")[0]
Write-Host "HEAD local|remote : $localHead | $remoteHead"

if ($TagName) {
  $localTag  = (git -C $PublishDir rev-list -n 1 $TagName).Trim()
  $remoteTag = ((git -C $PublishDir ls-remote origin "refs/tags/$TagName^{}") -split "`t")[0]
  Write-Host "TAG  local|remote : $localTag  | $remoteTag"
}

# AutoNotes (previous publish tag from source, if any)
$allPubTags   = git -C $SourceDir tag --list 'v27.1.0-bb*-publish' --sort=-creatordate
$prevTag      = ($allPubTags | Where-Object { $_ -ne $TagName } | Select-Object -First 1)
$changesHeader= if ($prevTag) { "### Changes since $prevTag" } else { "### Recent changes" }
$logRange     = if ($prevTag) { "$prevTag..$srcSHA" } else { $srcSHA }
$changes      = git -C $SourceDir log --no-merges --date=short --pretty="* %ad %h %s" $logRange 2>$null

$notes = @"
## BitcoBoost $TagName

**Snapshot:** commit $headShort
**Source:** commit $srcSHA
**Branch:** $Branch
**Asset:** $zipName
**SHA256:** $zipSha
$changesHeader
$changes
"@
$notes | Set-Clipboard

if ($OpenRelease -and $TagName) {
  $parts = $Remote -split '[:/]'
  $owner = $parts[$parts.Length - 2]
  $repo  = $repoName
  $url = "https://github.com/$owner/$repo/releases/new?tag=$TagName&title=$TagName"
  Start-Process $url
}

