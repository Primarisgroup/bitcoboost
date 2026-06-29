@echo off
cd /d D:\bitcoboost
REM Avvio BitcoBoost TESTNET (P2P 38210, RPC 38211, bind localhost)
start "BitcoBoost TEST" cmd /k "src\bitcoind.exe -datadir=D:\bitcoboost\bb_main -testnet -rpcport=38211"
