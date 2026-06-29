param([int]$N = 1)
$ErrorActionPreference = "Stop"
Write-Host "[bb-mine] mining $N blocks..."
& py -3 D:\bitcoboost\tools\mine_many_offline.py $N
