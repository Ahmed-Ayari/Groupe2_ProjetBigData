"""Resource sampling (psutil, whole process tree incl. JVM) and Spark event-log parsing."""
from __future__ import annotations
import json
import threading
import time
from pathlib import Path
import psutil


class Sampler:
    """Samples peak RSS of a process tree and mean system CPU while a child runs."""

    def __init__(self, pid: int, interval: float = 0.5):
        self.pid, self.interval = pid, interval
        self.peak_rss = 0
        self._cpu: list[float] = []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        try:
            root = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            return
        psutil.cpu_percent(interval=None)
        while not self._stop.is_set():
            try:
                procs = [root] + root.children(recursive=True)
                rss = 0
                for p in procs:
                    try:
                        rss += p.memory_info().rss
                    except psutil.Error:
                        pass
                self.peak_rss = max(self.peak_rss, rss)
                self._cpu.append(psutil.cpu_percent(interval=None))
            except psutil.Error:
                pass
            time.sleep(self.interval)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join(timeout=2)

    @property
    def peak_rss_mb(self) -> float:
        return self.peak_rss / 2**20

    @property
    def cpu_mean_pct(self) -> float:
        return sum(self._cpu) / len(self._cpu) if self._cpu else float("nan")


def parse_eventlog(event_dir: Path) -> dict:
    """Aggregate task metrics from Spark JSON event logs.

    P_effective = tasks of the LAST stage that read shuffle data (the P-governed aggregation, after AQE
    coalescing). The earlier repartition(Q) exchange of the file list is therefore not counted. For decode-only
    probes (no P shuffle) it reports the Q exchange.
    """
    shuffle_read = shuffle_write = spill = n_tasks = 0
    durs: list[float] = []
    stage_tasks: dict[int, int] = {}
    stage_reads: dict[int, int] = {}
    for f in sorted(Path(event_dir).rglob("*")):
        if not f.is_file():
            continue
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev = e.get("Event")
                if ev == "SparkListenerStageCompleted":
                    si = e["Stage Info"]
                    stage_tasks[si["Stage ID"]] = si.get("Number of Tasks", 0)
                elif ev == "SparkListenerTaskEnd":
                    tm = e.get("Task Metrics") or {}
                    ti = e.get("Task Info", {})
                    sr = tm.get("Shuffle Read Metrics", {})
                    rb = sr.get("Remote Bytes Read", 0) + sr.get("Local Bytes Read", 0)
                    shuffle_read += rb
                    shuffle_write += tm.get("Shuffle Write Metrics", {}).get("Shuffle Bytes Written", 0)
                    spill += tm.get("Disk Bytes Spilled", 0)
                    n_tasks += 1
                    sid = e.get("Stage ID")
                    stage_reads[sid] = stage_reads.get(sid, 0) + rb
                    durs.append((ti.get("Finish Time", 0) - ti.get("Launch Time", 0)) / 1000.0)
    readers = sorted(s for s, b in stage_reads.items() if b > 0)
    durs.sort()
    med = durs[len(durs) // 2] if durs else float("nan")
    return {
        "shuffle_read_bytes": shuffle_read, "shuffle_write_bytes": shuffle_write, "disk_spill_bytes": spill,
        "n_tasks": n_tasks, "task_time_median_s": med, "task_time_max_s": max(durs) if durs else float("nan"),
        "P_effective": stage_tasks.get(readers[-1], 0) if readers else 0,
    }
