param([string]$Python = "")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $Python) {
    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) { $Python = $VenvPython }
    else { $Python = "python" }
}
$env:PYTHONPATH = "src"
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("run_all-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
Start-Transcript -Path $Log | Out-Null

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "`n=== $Name ==="
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

try {
    Invoke-Step "pilot" { & $Python -m bigdata.campaign pilot }
    Invoke-Step "diagnose" { & $Python -m bigdata.diagnose }
    Invoke-Step "grid" { & $Python -m bigdata.campaign grid }
    $P = (& $Python scripts/select_grid_p.py).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Grid P selection failed with exit code $LASTEXITCODE"
    }
    Write-Host "`nUsing grid-selected P=$P for size-up."
    Invoke-Step "sizeup-cal" { & $Python -m bigdata.campaign sizeup-cal --P $P }
    Invoke-Step "fit" { & $Python -m bigdata.selector fit }
    Invoke-Step "sizeup-test" { & $Python -m bigdata.campaign sizeup-test --P $P }
    Invoke-Step "final" { & $Python -m bigdata.campaign final }
    Invoke-Step "evaluate" { & $Python -m bigdata.selector evaluate }
    Invoke-Step "plots" { & $Python -m bigdata.plots }
    Invoke-Step "report-facts" { & $Python -m bigdata.report_facts }
    Invoke-Step "package" { & $Python scripts/package.py }
    Write-Host "`nAll steps completed. Log: $Log"
} catch {
    Write-Error $_
    Write-Host "Completed run_ids are retained. Resume by rerunning: .\scripts\run_all.ps1"
    Write-Host "Log: $Log"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
