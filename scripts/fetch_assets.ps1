# Fetches the public assets this project runs on. Nothing here is redistributed in bulk.
# Usage: powershell -File scripts/fetch_assets.ps1 [-Manuals]
param([switch]$Manuals)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root = Split-Path $PSScriptRoot -Parent
$models = Join-Path $root "assets\models"
$docs = Join-Path $root "assets\docs"
New-Item -ItemType Directory -Force -Path $models, $docs | Out-Null

# NASA Airborne Science Program publishes these as GLB, one mesh per aircraft.
# Others follow the same pattern: C130_WFF, DC8_AFRC, B200_AFRC, C20A_AFRC, WB57_JSC, P3_WFF, ER2_AFRC
$airframes = @{
  "G3_LARC_GND_0824.glb"  = "https://airbornescience.nasa.gov/sites/default/files/pages/G3_LARC_GND_0824.glb"
  "C130_WFF_GND_0824.glb" = "https://airbornescience.nasa.gov/sites/default/files/pages/C130_WFF_GND_0824.glb"
}

foreach ($name in $airframes.Keys) {
  $out = Join-Path $models $name
  if (Test-Path $out) { Write-Host "have $name"; continue }
  Write-Host "fetching $name"
  Invoke-WebRequest -Uri $airframes[$name] -OutFile $out -UseBasicParsing
}

if ($Manuals) {
  # US Government works, public domain. Large: ~100 MB each, hence the flag.
  $handbooks = @{
    "FAA-H-8083-31B_airframe.pdf"   = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf"
    "FAA-H-8083-32B_powerplant.pdf" = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32B_Aviation_Maintenance_Technician_Handbook.pdf"
  }
  foreach ($name in $handbooks.Keys) {
    $out = Join-Path $docs $name
    if (Test-Path $out) { Write-Host "have $name"; continue }
    Write-Host "fetching $name (large)"
    Invoke-WebRequest -Uri $handbooks[$name] -OutFile $out -UseBasicParsing
  }
}

Get-ChildItem $models, $docs -File | ForEach-Object { "{0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB) }
