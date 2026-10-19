<#
  fix_cushion_runtime.ps1
  Forces Rhino 8 to use the Cushion v26.06 (port) Python runtime.

  Why this is needed:
    Rhino caches a plugin's Python at %USERPROFILE%\.rhinocode\libs\<hash>\.
    The <hash> is keyed to content, but the cache is NOT refreshed when you
    reinstall a package that reuses the same hash folder, and uninstalling a
    package never deletes it. So a machine that ever had the old 24.06 Cushion
    keeps serving the old runtime even after installing the 0.2.0 .yak.

  What this does:
    1. Finds the PORT runtime (sofagh with _load_plugins) inside your installed
       Cushion package (or inside a .yak you point it at).
    2. Overwrites every ~/.rhinocode/libs/*/sofagh with that port runtime,
       and creates the cache folder if missing.
    3. Deletes __pycache__ so stale .pyc can't shadow it.
    4. Verifies the result.

  Usage (Command Prompt or PowerShell), with Rhino CLOSED:
    powershell -ExecutionPolicy Bypass -File fix_cushion_runtime.ps1
  Optional, if the package copy is also old, point at the .yak file:
    powershell -ExecutionPolicy Bypass -File fix_cushion_runtime.ps1 -YakPath "C:\path\cushion-0.2.0-any-any.yak"
#>

param(
    [string]$YakPath = ""
)

$ErrorActionPreference = "Stop"
function Say($m){ Write-Host $m }
function Die($m){ Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

# --- 0. Rhino must be closed (it caches modules in memory) -------------------
if (Get-Process -Name "Rhino" -ErrorAction SilentlyContinue) {
    Die "Rhino is running. Fully quit Rhino, then run this again."
}

$pkgRoot = Join-Path $env:APPDATA "McNeel\Rhinoceros\packages\8.0\Cushion"
$rhcLibs = Join-Path $env:USERPROFILE ".rhinocode\libs"

# --- 1. Locate a PORT sofagh (runtime/scene.py containing _load_plugins) ------
function Find-PortSofagh($searchRoot){
    if (-not (Test-Path $searchRoot)) { return $null }
    $hits = Get-ChildItem -Path $searchRoot -Recurse -Filter "scene.py" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "sofagh[\\/]runtime[\\/]scene\.py$" } |
            Where-Object { Select-String -Path $_.FullName -Pattern "_load_plugins" -Quiet }
    if (-not $hits) { return $null }
    # sofagh dir = parent of runtime dir = scene.py -> runtime -> sofagh
    return (Split-Path (Split-Path $hits[0].FullName -Parent) -Parent)
}

$portSofagh = $null

# Highest priority: a 'sofagh' folder shipped NEXT TO this script (self-contained,
# carries the teleop/Windows fixes). Use it if present and it is the port runtime.
$bundled = Join-Path $PSScriptRoot "sofagh"
if (Test-Path (Join-Path $bundled "runtime\scene.py")) {
    if (Select-String -Path (Join-Path $bundled "runtime\scene.py") -Pattern "_load_plugins" -Quiet) {
        $portSofagh = $bundled
        Say "Using bundled runtime next to script: $portSofagh"
    }
}

if ($portSofagh) {
    # skip the other sources
} elseif ($YakPath -ne "") {
    if (-not (Test-Path $YakPath)) { Die "YakPath not found: $YakPath" }
    $tmp = Join-Path $env:TEMP ("cushion_yak_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Say "Extracting $YakPath ..."
    tar -xzf $YakPath -C $tmp
    $portSofagh = Find-PortSofagh $tmp
    if (-not $portSofagh) { Die "No PORT runtime (_load_plugins) found inside that .yak." }
    Say "Port runtime found in .yak: $portSofagh"
} else {
    $portSofagh = Find-PortSofagh $pkgRoot
    if (-not $portSofagh) {
        Die ("No PORT runtime found in installed package ($pkgRoot).`n" +
             "Install the 0.2.0 .yak first (PackageManager -> Install from file),`n" +
             "or re-run with:  -YakPath `"C:\path\cushion-0.2.0-any-any.yak`"")
    }
    Say "Port runtime found in installed package: $portSofagh"
}

# --- 2. Overwrite every cached sofagh with the port copy ----------------------
if (-not (Test-Path $rhcLibs)) {
    New-Item -ItemType Directory -Path $rhcLibs | Out-Null
    Say "Created $rhcLibs"
}

# existing cached sofagh dirs
$targets = @()
Get-ChildItem -Path $rhcLibs -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $cand = Join-Path $_.FullName "sofagh"
    if (Test-Path $cand) { $targets += $cand }
}
# ensure the known hash folder exists so Rhino finds it even on a clean cache
$known = Join-Path $rhcLibs "IRWxNyp1\sofagh"
if ($targets -notcontains $known) { $targets += $known }

foreach ($t in $targets) {
    if (Test-Path $t) { Remove-Item -Path $t -Recurse -Force }
    $parent = Split-Path $t -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    Copy-Item -Path $portSofagh -Destination $t -Recurse -Force
    Say "Updated: $t"
}

# --- 3. Purge bytecode caches -------------------------------------------------
Get-ChildItem -Path $rhcLibs -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force }
Say "Purged __pycache__."

# --- 4. Verify ----------------------------------------------------------------
Say ""
Say "Verification (expect 'PORT' for each):"
$ok = $true
foreach ($t in $targets) {
    $sp = Join-Path $t "runtime\scene.py"
    if (Test-Path $sp) {
        $isPort = Select-String -Path $sp -Pattern "_load_plugins" -Quiet
        $hasOld = Select-String -Path $sp -Pattern "SofaSimpleFem" -Quiet
        $tag = if ($isPort -and -not $hasOld) { "PORT" } else { "OLD/BAD"; $ok = $false }
        Say ("  [{0}] {1}" -f $tag, $sp)
    }
}
Say ""
if ($ok) {
    Say "DONE. Start Rhino, drop SofaScene (write=True) + SofaRun (run=True),"
    Say "point them at your 3 paths, and it will launch the v26.06 SOFA scene."
} else {
    Die "Something is still old. Re-run with -YakPath pointing at the 0.2.0 .yak."
}
