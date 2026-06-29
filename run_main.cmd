@echo off
cd /d D:\bitcoboost
REM Avvio BitcoBoost mainnet con RPC sicuro su localhost:38201
start "BitcoBoost MAIN" cmd /k "src\bitcoind.exe -datadir=D:\bitcoboost\bb_main -rpcport=38201"
timeout /t 2 >nul
echo --- Porte in ascolto ---
netstat -ano | find "38200"
netstat -ano | find "38201"
echo Per fermare: src\bitcoin-cli.exe -datadir=D:\bitcoboost\bb_main -rpcport=38201 stop
