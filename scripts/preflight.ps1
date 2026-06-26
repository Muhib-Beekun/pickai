$ErrorActionPreference = 'Stop'
Write-Host '=== PickAI Preflight ==='

function Test-Command($name) {
  if (Get-Command $name -ErrorAction SilentlyContinue) { Write-Host "[OK] $name" }
  else { Write-Host "[MISSING] $name"; $script:fail = $true }
}

$fail = $false
Test-Command python
Test-Command git
Test-Command pip
Test-Command nvidia-smi
Test-Command ollama

python -c "import sys; assert sys.version_info >= (3, 11), sys.version"
Write-Host '[OK] Python version'

$disk = (Get-PSDrive C).Free / 1GB
Write-Host "C: free ${disk} GB"
if ($disk -lt 15) { Write-Host '[WARN] Low disk — consider D: cache symlink' }

if ($fail) { exit 1 }
Write-Host '=== Preflight passed ==='
