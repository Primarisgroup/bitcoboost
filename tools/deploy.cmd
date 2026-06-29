@echo off
setlocal enabledelayedexpansion

echo === Bitcoboost deploy start ===

rem Imposta default se non arriva da variabile progetto
if "%DEPLOY_TARGET_DIR%"=="" (
  set "DEPLOY_TARGET_DIR=D:\Sites\bitcoboost"
)

echo Target: "%DEPLOY_TARGET_DIR%"

rem Crea la cartella target se non esiste
if not exist "%DEPLOY_TARGET_DIR%" (
  mkdir "%DEPLOY_TARGET_DIR%"
  if errorlevel 1 (
    echo ERRORE: impossibile creare la cartella "%DEPLOY_TARGET_DIR%"
    exit /b 2
  )
)

rem Contenuto sorgente (cartella dist dall'artefatto build)
if not exist "dist" (
  echo ERRORE: cartella "dist" non trovata. Hai eseguito il job build?
  exit /b 3
)

echo Copia file con ROBOCOPY...
robocopy "dist" "%DEPLOY_TARGET_DIR%" /E /NFL /NDL /NP /NJH /NJS /R:1 /W:1 > robocopy.log

set RC=%ERRORLEVEL%
if %RC% LSS 8 (
  echo Deploy COMPLETATO. (robocopy RC=%RC%)
  exit /b 0
) else (
  echo ERRORE: Robocopy ha restituito RC=%RC%
  exit /b %RC%
)
