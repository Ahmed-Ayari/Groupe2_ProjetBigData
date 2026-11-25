"""Run one experiment in a subprocess with timeout, sample resources, parse Spark logs, check equivalence, log one CSV row."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, platform, shutil, subprocess, sys, tempfile, time
from dataclasses import dataclass, asdict, field
from pathlib import Path
import pandas as pd
import psutil

from .config import ROOT, load_config, resolve
from .metrics import Sampler, parse_eventlog
from .equivalence import check_run

COLUMNS = ["run_id", "lot_id", "code_version", "environment_id", "workload", "policy", "p", "cores_per_node",
           "memory_per_node", "Q_read", "P_initial", "P_effective", "AQE", "cache_policy", "source_bytes",
           "prepared_bytes", "duration_s", "submit_duration_s", "shuffle_read_bytes", "shuffle_write_bytes",
           "disk_spill_bytes", "deadline_s", "status", "output_check", "repetition", "timestamp"]
EXTRA = ["method", "dataset", "engine", "scope", "stop_after", "strategy", "peak_rss_mb", "cpu_mean_pct",
         "task_time_median_s", "task_time_max_s", "n_tasks", "cold_or_warm", "split", "error"]
ALL = COLUMNS + EXTRA


@dataclass
class Spec:
    method: str                    # B0..B4, B4_nomargin, PILOT, GRID, ...
    dataset: str                   # metropt | ukdale
    engine: str                    # local | spark
    lot: str = "metropt3"
    workload: str = "A"
    scope: str = "raw"
    policy: str = "grid"
    p: int = 1
    P: int = 64
    Q: int = 8
    aqe: int = 1
    strategy: str = "hash"
    stop_after: str = "write"
    repetition: int = 1
    deadline_s: float | None = None
    split: str = ""
    timeout_s: int | None = None

    def run_id(self) -> str:
        key = "-".join(str(v) for v in (self.method, self.dataset, self.lot, self.workload, self.engine, self.scope,
                                         self.policy, self.p, self.P, self.Q, self.aqe, self.strategy,
                                         self.stop_after, self.repetition))
        return f"{self.method}-{self.dataset}-{self.lot}-{hashlib.sha1(key.encode()).hexdigest()[:10]}-r{self.repetition}"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "no-git"


def environment_id(cfg: dict) -> str:
    f = ROOT / "environment" / "hardware.json"
    if f.exists():
        return json.loads(f.read_text()).get("environment_id", "unknown")
    return "unknown"


def completed_ids(runs_csv: Path) -> set[str]:
    if not runs_csv.exists():
        return set()
    df = pd.read_csv(runs_csv, usecols=["run_id", "status"])
    return set(df.loc[df.status.isin(["OK", "TIMEOUT", "EQUIV_FAIL"]), "run_id"])


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALL, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def run_experiment(spec: Spec, cfg: dict | None = None, results_dir: Path | None = None, force: bool = False) -> dict:
    cfg = cfg or load_config()
    results = results_dir or resolve(cfg, "results")
    runs_csv, failed_csv = results / "runs.csv", results / "failed_runs.csv"
    rid = spec.run_id()
    if not force and rid in completed_ids(runs_csv):
        return {"run_id": rid, "status": "SKIPPED"}
    timeout = spec.timeout_s or cfg["run"]["timeout_s"]
    out = results / "out" / rid
    ev = results / "eventlogs" / rid
    for d in (out, ev):
        shutil.rmtree(d, ignore_errors=True)
    rj = Path(tempfile.mkstemp(suffix=".json")[1])
    cmd = [sys.executable, "-m", "bigdata.run_one", "--dataset", spec.dataset, "--engine", spec.engine,
           "--workload", spec.workload, "--scope", spec.scope, "--lot", spec.lot, "--p", str(spec.p), "--P", str(spec.P),
           "--Q", str(spec.Q), "--aqe", str(spec.aqe), "--strategy", spec.strategy, "--stop-after", spec.stop_after,
           "--out", str(out), "--event-dir", str(ev), "--result-json", str(rj)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
               BIGDATA_CONFIG=os.environ.get("BIGDATA_CONFIG", str(ROOT / "configs" / "default.yaml")))
    status, err, res = "OK", "", {}
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    with Sampler(proc.pid) as smp:
        try:
            _, stderr = proc.communicate(timeout=timeout)
            if proc.returncode != 0:
                status, err = "ERROR", stderr.decode(errors="ignore")[-600:]
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            try:
                for c in psutil.Process(proc.pid).children(recursive=True):
                    c.kill()
            except psutil.Error:
                pass
            proc.kill()
            proc.communicate()
    submit = time.perf_counter() - t0
    if status == "OK" and rj.exists() and rj.stat().st_size:
        res = json.loads(rj.read_text())
    rj.unlink(missing_ok=True)

    metrics = parse_eventlog(ev) if spec.engine == "spark" and ev.exists() else {}
    check = "not_applicable"
    if status == "OK" and spec.stop_after == "write" and out.exists():
        ref = results / "reference" / f"{spec.dataset}_{spec.lot}_{spec.workload}.parquet"
        kind = spec.dataset
        if spec.engine == "local" and not ref.exists():
            ref.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(out, ref)
            check = "reference_created"
        elif ref.exists():
            r = check_run(out, ref, cfg, kind, rid, results)
            check = "ok" if r["ok"] else "fail"
            if not r["ok"]:
                status = "EQUIV_FAIL"
        else:
            check = "no_reference"
    shutil.rmtree(out, ignore_errors=True)

    row = {
        "run_id": rid, "lot_id": spec.lot, "code_version": git_hash(), "environment_id": environment_id(cfg),
        "workload": spec.workload, "policy": spec.policy, "p": spec.p, "cores_per_node": 1,
        "memory_per_node": cfg["spark"]["driver_memory"], "Q_read": spec.Q if spec.dataset == "ukdale" else "",
        "P_initial": spec.P if spec.engine == "spark" else "", "P_effective": metrics.get("P_effective", ""),
        "AQE": spec.aqe if spec.engine == "spark" else "", "cache_policy": cfg["spark"]["cache_policy"],
        "source_bytes": res.get("source_bytes", ""), "prepared_bytes": res.get("prepared_bytes", ""),
        "duration_s": float(timeout) if status == "TIMEOUT" else res.get("duration_s", ""),
        "submit_duration_s": submit, "shuffle_read_bytes": metrics.get("shuffle_read_bytes", ""),
        "shuffle_write_bytes": metrics.get("shuffle_write_bytes", ""), "disk_spill_bytes": metrics.get("disk_spill_bytes", ""),
        "deadline_s": spec.deadline_s if spec.deadline_s is not None else "", "status": status, "output_check": check,
        "repetition": spec.repetition, "timestamp": pd.Timestamp.now("UTC").isoformat(),
        "method": spec.method, "dataset": spec.dataset, "engine": spec.engine, "scope": spec.scope,
        "stop_after": spec.stop_after, "strategy": spec.strategy, "peak_rss_mb": round(smp.peak_rss_mb, 1),
        "cpu_mean_pct": round(smp.cpu_mean_pct, 1), "task_time_median_s": metrics.get("task_time_median_s", ""),
        "task_time_max_s": metrics.get("task_time_max_s", ""), "n_tasks": metrics.get("n_tasks", ""),
        "cold_or_warm": "os_cache_not_controlled", "split": spec.split, "error": err.replace("\n", " | ")[:400],
    }
    append_row(runs_csv, row)
    if status != "OK":
        append_row(failed_csv, row)
    return row


def collect_environment(cfg: dict) -> dict:
    """Write environment/hardware.json and versions.txt."""
    import numpy, pandas
    try:
        import pyspark
        spark_v = pyspark.__version__
    except Exception:
        spark_v = "missing"
    java = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()
    free = shutil.disk_usage(ROOT).free / 2**30
    info = {"cpu_logical": os.cpu_count(), "cpu_physical": psutil.cpu_count(logical=False),
            "ram_gb": round(psutil.virtual_memory().total / 2**30, 1), "disk_free_gb": round(free, 1),
            "os": platform.platform(), "python": platform.python_version(), "java": next((l for l in java if "version" in l), "missing"),
            "pyspark": spark_v, "numpy": numpy.__version__, "pandas": pandas.__version__}
    info["environment_id"] = f"{info['cpu_physical']}c-{info['ram_gb']}g-spark{spark_v}"
    (ROOT / "environment").mkdir(exist_ok=True)
    (ROOT / "environment" / "hardware.json").write_text(json.dumps(info, indent=2))
    pip = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    (ROOT / "environment" / "versions.txt").write_text(pip)
    return info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", action="store_true", help="collect hardware/version info and exit")
    ap.add_argument("--method", default="MANUAL")
    ap.add_argument("--dataset"); ap.add_argument("--engine"); ap.add_argument("--lot", default="metropt3")
    ap.add_argument("--workload", default="A"); ap.add_argument("--scope", default="raw")
    ap.add_argument("--p", type=int, default=1); ap.add_argument("--P", type=int, default=64)
    ap.add_argument("--Q", type=int, default=8); ap.add_argument("--aqe", type=int, default=1)
    ap.add_argument("--strategy", default="hash"); ap.add_argument("--stop-after", default="write")
    ap.add_argument("--rep", type=int, default=1)
    a = ap.parse_args()
    if a.env:
        print(json.dumps(collect_environment(load_config()), indent=2))
    else:
        print(run_experiment(Spec(a.method, a.dataset, a.engine, a.lot, a.workload, a.scope, "manual", a.p, a.P, a.Q,
                                  a.aqe, a.strategy, a.stop_after, a.rep)))
