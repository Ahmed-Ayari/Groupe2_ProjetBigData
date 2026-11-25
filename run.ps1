# Windows replacement for the Makefile. Usage (from the project folder, venv activated):
#   .\run.ps1 setup | env | test | smoke | metropt | lots | download | pilot | grid | fit | final | evaluate | mining | plots | package
#   .\run.ps1 ukdale-list "2013/wk11"  (start with one week; optional -MaxFiles 500 -Filelist urls.txt)
#   .\run.ps1 ukdale-debug "2013/wk11"
#   .\run.ps1 sizeup-cal 64      (second argument = P)
#   .\run.ps1 sizeup-test 64
# If scripts are blocked: Set-ExecutionPolicy -Scope Process Bypass
param([Parameter(Mandatory=$true)][string]$Target, [string]$Arg = "", [int]$MaxFiles = 500, [string]$Filelist = "")
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"
function Py { python @args; if ($LASTEXITCODE -ne 0) { throw "failed: python $args" } }
function Smoke { $env:BIGDATA_CONFIG = "configs/smoke.yaml" }
function Real { Remove-Item Env:BIGDATA_CONFIG -ErrorAction SilentlyContinue }

switch ($Target) {
  "setup"   { Py -m pip install -r requirements.txt }
  "env"     { Real; Py -m bigdata.runner --env }
  "test"    { Smoke; Py -m pytest tests -q }
  "smoke"   {
      Smoke
      Py scripts/make_smoke_data.py
      Py -m bigdata.campaign pilot --lot cal_1
      Py -m bigdata.campaign grid --lot cal_2
      Py -m bigdata.campaign sizeup-cal --P 16
      Py -m bigdata.selector fit
      Py -m bigdata.campaign final
      Py -m bigdata.selector evaluate }
  "metropt" { Real; Py -m bigdata.acquire metropt; Py -m bigdata.audit; Py -m bigdata.prepare metropt }
  "ukdale-list" {
      Real
      if ($Filelist) { Py -m bigdata.acquire ukdale-list --filelist $Filelist --max-files $MaxFiles }
      else { $w = $Arg -split "\s+"; Py -m bigdata.acquire ukdale-list --weeks @w --max-files $MaxFiles }
  }
  "ukdale-debug" { Real; Py -m bigdata.acquire ukdale-debug --week $Arg }
  "lots"    { Real; Py -m bigdata.lots }
  "download" { Real; Py -m bigdata.acquire ukdale-download --lots cal_1 cal_2 cal_3 test_1 test_2 test_3 }
  "pilot"   { Real; Py -m bigdata.campaign pilot; Py -m bigdata.diagnose }
  "grid"    { Real; Py -m bigdata.campaign grid }
  "sizeup-cal"  { Real; Py -m bigdata.campaign sizeup-cal --P $Arg }
  "sizeup-test" { Real; Py -m bigdata.campaign sizeup-test --P $Arg }
  "fit"     { Real; Py -m bigdata.selector fit }
  "final"   { Real; Py -m bigdata.campaign final }
  "evaluate" { Real; Py -m bigdata.selector evaluate }
  "mining"  { Real; Py -m bigdata.mining }
  "plots"   { Real; Py -m bigdata.plots; Py -m bigdata.report_facts }
  "package" { Py scripts/package.py }
  default   { throw "unknown target $Target" }
}
