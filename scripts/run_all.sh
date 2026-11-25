#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
if [[ -z "${PY:-}" && -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
else
    PY="${PY:-python}"
fi
mkdir -p logs
LOG="logs/run_all-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

resume_hint() {
    status=$?
    if (( status != 0 )); then
        printf '\nStopped with exit code %s. Completed run_ids are retained.\n' "$status"
        printf 'Resume by rerunning: bash scripts/run_all.sh\n'
        printf 'Log: %s\n' "$LOG"
    fi
    exit "$status"
}
trap resume_hint ERR

run_step() {
    printf '\n=== %s ===\n' "$1"
    shift
    "$@"
}

run_step pilot "$PY" -m bigdata.campaign pilot
run_step diagnose "$PY" -m bigdata.diagnose
run_step grid "$PY" -m bigdata.campaign grid
P="$("$PY" scripts/select_grid_p.py)"
printf '\nUsing grid-selected P=%s for size-up.\n' "$P"
run_step sizeup-cal "$PY" -m bigdata.campaign sizeup-cal --P "$P"
run_step fit "$PY" -m bigdata.selector fit
run_step sizeup-test "$PY" -m bigdata.campaign sizeup-test --P "$P"
run_step final "$PY" -m bigdata.campaign final
run_step evaluate "$PY" -m bigdata.selector evaluate
run_step plots "$PY" -m bigdata.plots
run_step report-facts "$PY" -m bigdata.report_facts
run_step package "$PY" scripts/package.py
printf '\nAll steps completed. Log: %s\n' "$LOG"
