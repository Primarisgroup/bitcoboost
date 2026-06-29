param(
  [Parameter(Mandatory=$true)]
  [string]$Tag,                                # es: v27.1.0-bb19-publish
  [string]$RepoSlug = "Maxtwin22/bitcoboost2", # owner/repo su GitHub
  [string]$Branch   = "phase2-branding",
  [string]$SrcRepo  = "D:\bitcoboost",
  [string]$PublishDir = "D:\bb_publish2",
  [string]$PrevTag = ""                        # opzionale: se omesso, lo calcolo
)

$ErrorActionPreference = "Stop"

# 0) Esegui publish snapshot + tag (senza aprire il browser)
& "$SrcRepo\tools\bb-publish-snapshot.ps1" -TagName $Tag -TagMessage "snapshot $Tag"  | Out-Host

# 1) ZIP + SHA256 (riusa quanto generato dallo script)
$zip = Get-ChildItem "$PublishDir\*-snapshot.zip" | Sort-Object LastWriteTime -Desc | Select-Object -First 1
if (-not $zip) { throw "ZIP non trovato in $PublishDir" }
$zipPath = $zip.FullName
$zipName = $zip.Name
$sha256  = (Get-FileHash $zipPath -Algorithm SHA256).Hash
$commit  = git -C $PublishDir rev-parse --short HEAD

# 2) Determina PrevTag (dal remoto) se non fornito
git -C $PublishDir fetch origin --tags --prune | Out-Null
if ([string]::IsNullOrEmpty($PrevTag)) {
  $allTags = (git -C $PublishDir ls-remote origin "refs/tags/*") `
    | ForEach-Object { ($_ -split "`t")[1] } `
    | Where-Object { $_ -notmatch '\^\{\}$' } `
    | ForEach-Object { $_ -replace '^refs/tags/','' }

  # Prendi l'ultimo "*-publish" diverso da $Tag, preferendo quello con numero bb più alto
  $pub = $allTags | Where-Object { $_ -match '^v27\.1\.0-bb\d+-publish$' -and $_ -ne $Tag } `
                   | ForEach-Object { [pscustomobject]@{ Name = $_; Num = [int](($_ -replace '^v27\.1\.0-bb(\d+)-publish$','$1')) } } `
                   | Sort-Object Num -Descending | Select-Object -First 1
  if ($pub) { $PrevTag = $pub.Name } else { $PrevTag = $null }
}

# 3) Genera body release (se ho un tag precedente provo il changelog)
$notes = @()
if ($PrevTag) {
  try {
    $notes = git -C $PublishDir log --no-merges --date=short --pretty="* %ad %h %s" "$PrevTag..$Tag"
  } catch { $notes = @() }
}

$body = @"
## BitcoBoost $Tag

**Snapshot:** commit $commit  
**Branch:** $Branch  
**Asset:** $zipName  
**SHA256:** $sha256
"@

if ($PrevTag) {
  $body += "`r`n`r`n### Changes since $PrevTag`r`n"
  if ($notes.Count -gt 0) { $body += ($notes -join "`r`n") } else { $body += "- Snapshot refresh." }
} else {
  $body += "`r`n`r`n### Notes`r`n- Initial publish or previous tag not found."
}

# 4) Crea/aggiorna Release via GitHub CLI (se disponibile), altrimenti fallback
$bodyFile = Join-Path $PublishDir "RELEASE-$Tag.md"
$body | Set-Content -Encoding UTF8 $bodyFile

$Gh = Get-Command gh -ErrorAction SilentlyContinue
if ($Gh) {
  # esiste già la release?
  $exists = $false
  try { gh release view "$Tag" --repo "$RepoSlug" *> $null; if ($LASTEXITCODE -eq 0) { $exists = $true } } catch {}

  if ($exists) {
    gh release edit "$Tag" --repo "$RepoSlug" --title "$Tag" --notes-file "$bodyFile" | Out-Host
    gh release upload "$Tag" "$zipPath" --repo "$RepoSlug" --clobber | Out-Host
  } else {
    gh release create "$Tag" "$zipPath" --repo "$RepoSlug" --title "$Tag" --notes-file "$bodyFile" --target "$Branch" | Out-Host
  }
  Write-Host ""
  Write-Host "Release aggiornata/creata: https://github.com/$RepoSlug/releases/tag/$Tag"
} else {
  # Fallback: apri pagina release e copia note negli appunti
  $url = "https://github.com/{0}/releases/new?tag={1}&title={1}" -f $RepoSlug, $Tag
  Set-Clipboard -Value $body
  Start-Process $url
  Write-Host ""
  Write-Host "GitHub CLI non trovato. Ho copiato le NOTE negli appunti e aperto la pagina:"
  Write-Host "URL: $url"
  Write-Host "Allega asset: $zipPath"
}

# 5) Output riepilogo
Write-Host ""
Write-Host "ZIP     : $zipPath"
Write-Host "SHA256  : $sha256"
Write-Host "HEAD    : $commit"
