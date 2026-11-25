"""Selective, resumable acquisition with SHA-256 and a disk guard.

UNVERIFIED IN CI: the sandbox used to write this code had no access to UCI/CEDA. Run `--dry-run` first.
The CEDA directory listing format is parsed with a tolerant href regex; if it fails, pass `--filelist`
(one URL or path relative to the version_0 base per line).
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, re, shutil, time, zipfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import pandas as pd
import requests

from .config import load_config, resolve
from .lots import lot_targets
from .ukdale import FNAME, file_start_ns

HDR = {"User-Agent": "Groupe2-ProjetBigData/1.0 (academic dataset retrieval)"}
RETRY_STATUSES = {429, *range(500, 600)}
MAX_HEAD_WORKERS = 2
DEFAULT_MAX_FILES = 500


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while b := fh.read(chunk):
            h.update(b)
    return h.hexdigest()


def free_gb(path: Path) -> float:
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free / 2**30


def _retry_delay(response, attempt: int) -> float:
    fallback = float(2**attempt)
    value = response.headers.get("Retry-After")
    if not value:
        return fallback
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return fallback
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def request_with_retry(method: str, url: str, *, retries: int = 5, **kwargs):
    """Retry temporary CEDA responses, respecting Retry-After when supplied."""
    request = getattr(requests, method.lower())
    for attempt in range(retries + 1):
        response = request(url, **kwargs)
        if response.status_code not in RETRY_STATUSES or attempt == retries:
            return response
        delay = _retry_delay(response, attempt)
        print(f"HTTP {response.status_code} for {url}; retrying in {delay:g}s")
        time.sleep(delay)
    raise RuntimeError("unreachable retry state")


def download(url: str, dest: Path, min_free_gb: float, retries: int = 5, dry_run: bool = False) -> Path:
    """Resumable download with exponential backoff. Stops if free disk falls under the guard."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"[dry-run] GET {url} -> {dest}")
        return dest
    for attempt in range(retries):
        try:
            if free_gb(dest.parent) < min_free_gb:
                raise RuntimeError(f"disk guard: less than {min_free_gb} GB free, stopping")
            have = dest.stat().st_size if dest.exists() else 0
            h = dict(HDR, **({"Range": f"bytes={have}-"} if have else {}))
            with requests.get(url, headers=h, stream=True, timeout=60) as r:
                if r.status_code == 416:      # already complete
                    return dest
                r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with open(dest, mode) as fh:
                    for blk in r.iter_content(1 << 20):
                        fh.write(blk)
            return dest
        except RuntimeError:
            raise
        except Exception as exc:
            wait = 2 ** attempt
            print(f"retry {attempt + 1}/{retries} after {wait}s: {exc}")
            time.sleep(wait)
    raise RuntimeError(f"failed to download {url}")


# ---------------------------------------------------------------- MetroPT-3 --------------------
def acquire_metropt(cfg: dict, dry_run: bool = False) -> dict:
    raw, prep, man = resolve(cfg, "data_raw"), resolve(cfg, "data_prepared"), resolve(cfg, "manifests")
    z = raw / "metropt" / "metropt3.zip"
    download(cfg["metropt"]["url"], z, cfg["paths"]["min_free_disk_gb"], dry_run=dry_run)
    if dry_run:
        return {}
    with zipfile.ZipFile(z) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        zf.extract(csvs[0], raw / "metropt")
    csv_path = raw / "metropt" / csvs[0]
    m = {"dataset": "MetroPT-3", "doi": "10.24432/C5VW3R", "license": "CC BY 4.0", "url": cfg["metropt"]["url"],
         "download_date": pd.Timestamp.now("UTC").isoformat(), "zip_sha256": sha256_file(z), "csv_path": str(csv_path),
         "csv_sha256": sha256_file(csv_path), "csv_bytes": csv_path.stat().st_size,
         "parquet_path": str(prep / "metropt.parquet")}
    man.mkdir(parents=True, exist_ok=True)
    (man / "metropt3.json").write_text(json.dumps(m, indent=2))
    return m


# ---------------------------------------------------------------- UK-DALE ----------------------
class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def parse_listing(html: str) -> list[str]:
    parser = _HrefParser()
    parser.feed(html)
    return parser.hrefs


def _version_relative_path(value: str, directory_url: str | None = None) -> str | None:
    candidate = urljoin(directory_url, value) if directory_url else value
    parsed = urlsplit(candidate)
    if parsed.hostname and parsed.hostname.lower() not in {"data.ceda.ac.uk", "dap.ceda.ac.uk"}:
        return None
    path = unquote(parsed.path)
    marker = "/version_0/"
    if marker in path:
        rel = path.split(marker, 1)[1]
    elif not parsed.scheme and not parsed.netloc and not path.startswith("/"):
        rel = path
    else:
        return None
    rel = rel.lstrip("/")
    if not rel.lower().endswith(".flac") or ".." in Path(rel).parts:
        return None
    return rel


def parse_filelist(path: Path) -> list[str]:
    """Accept relative paths or full .flac URLs copied from the CEDA browser."""
    rel = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        item = _version_relative_path(value)
        if item is None:
            raise ValueError(f"not a recognized UK-DALE .flac URL/path: {value}")
        if not FNAME.search(item):
            raise ValueError(f"UK-DALE filename does not match expected timestamp format: {value}")
        rel.append(item)
    return sorted(set(rel), key=file_start_ns)


def _cache_path(cfg: dict) -> Path:
    return resolve(cfg, "manifests") / "ukdale_listing_cache.json"


def _load_listing_cache(path: Path) -> dict:
    if not path.exists():
        return {"weeks": {}, "sizes": {}}
    cache = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cache, dict) or not isinstance(cache.get("weeks"), dict) or not isinstance(cache.get("sizes"), dict):
        raise ValueError(f"invalid UK-DALE listing cache: {path}")
    return cache


def _save_listing_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def list_dir(url: str) -> str:
    response = request_with_retry("get", url, headers=HDR, timeout=60)
    response.raise_for_status()
    return response.text


def _week_files(html: str, directory_url: str, house: str, week: str) -> list[str]:
    expected_prefix = f"{house}/{week.strip('/')}/"
    files = set()
    for href in parse_listing(html):
        rel = _version_relative_path(href, directory_url)
        if rel and rel.startswith(expected_prefix) and FNAME.search(rel):
            files.add(rel)
    return sorted(files, key=file_start_ns)


def crawl_weeks(base: str, house: str, weeks: list[str], cache: dict) -> list[str]:
    """Read cached week listings or fetch only missing pages from the CEDA browse host."""
    for week in weeks:
        if week in cache["weeks"]:
            continue
        directory = urljoin(base, f"{house}/{week.strip('/')}/")
        files = _week_files(list_dir(directory), directory, house, week)
        if not files:
            message = (
                f"No .flac links were found in {directory}. The page may be JavaScript-rendered. "
                "Save the .flac URLs copied from the browser, one per line, then rerun with --filelist PATH."
            )
            raise SystemExit(message)
        cache["weeks"][week] = files
    return sorted({f for week in weeks for f in cache["weeks"][week]}, key=file_start_ns)


def head_size(url: str) -> int:
    download_url = url if "?" in url else f"{url}?download=1"
    response = request_with_retry("head", download_url, headers=HDR, timeout=60, allow_redirects=True)
    response.raise_for_status()
    try:
        return int(response.headers["Content-Length"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"missing/invalid Content-Length for {download_url}") from exc


def _lot_targets(cfg: dict) -> list[tuple[str, str, float]]:
    return lot_targets(cfg["lots"]["calibration_gb"], cfg["lots"]["test_gb"])


def _covers_lots(
    files: list[str],
    sizes: dict[str, int],
    targets: list[tuple[str, str, float]],
    gap_files: int = 1,
    min_ratio: float = 4,
) -> bool:
    index = 0
    realized_sizes: dict[str, list[int]] = {}
    for target_i, (_, split, target_gb) in enumerate(targets):
        target_bytes = target_gb * 2**30
        is_largest = not any(later_split == split for _, later_split, _ in targets[target_i + 1:])
        goal_bytes = target_bytes
        if is_largest and realized_sizes.get(split):
            goal_bytes = max(goal_bytes, min(realized_sizes[split]) * min_ratio)
        total = 0
        while total < goal_bytes:
            if index >= len(files) or files[index] not in sizes:
                return False
            total += sizes[files[index]]
            index += 1
        realized_sizes.setdefault(split, []).append(total)
        if target_i < len(targets) - 1:
            index += gap_files
            if index > len(files):
                return False
    return True


def build_ukdale_manifest(
    cfg: dict,
    weeks: list[str] | None,
    filelist: Path | None,
    max_files: int = DEFAULT_MAX_FILES,
    workers: int = MAX_HEAD_WORKERS,
) -> pd.DataFrame:
    if max_files < 1:
        raise ValueError("--max-files must be at least 1")
    u, raw, man = cfg["ukdale"], resolve(cfg, "data_raw"), resolve(cfg, "manifests")
    cache_file = _cache_path(cfg)
    cache = _load_listing_cache(cache_file)
    if filelist:
        candidates = parse_filelist(filelist)
    else:
        requested_weeks = weeks or []
        if not requested_weeks:
            raise ValueError("provide --weeks or --filelist")
        candidates = crawl_weeks(u["list_base_url"], u["house"], requested_weeks, cache)
        _save_listing_cache(cache_file, cache)

    candidates = sorted(set(candidates), key=file_start_ns)[:max_files]
    if not candidates:
        raise ValueError("no valid UK-DALE .flac files were supplied")

    sizes: dict[str, int] = {str(k): int(v) for k, v in cache["sizes"].items()}
    targets = _lot_targets(cfg)
    min_ratio = float(cfg["lots"]["min_ratio_extremes"])
    head_workers = min(max(1, workers), MAX_HEAD_WORKERS)
    processed: list[str] = []
    index = 0
    with cf.ThreadPoolExecutor(max_workers=head_workers) as pool:
        while index < len(candidates):
            batch = []
            while index < len(candidates) and len(batch) < head_workers:
                rel = candidates[index]
                processed.append(rel)
                if rel not in sizes:
                    batch.append((rel, pool.submit(head_size, urljoin(u["base_url"], rel))))
                index += 1
                if _covers_lots(processed, sizes, targets, min_ratio=min_ratio):
                    break
            for rel, future in batch:
                sizes[rel] = future.result()
            cache["sizes"].update({rel: sizes[rel] for rel in processed if rel in sizes})
            _save_listing_cache(cache_file, cache)
            if _covers_lots(processed, sizes, targets, min_ratio=min_ratio):
                break

    selected = processed
    df = pd.DataFrame({
        "dataset": "UK-DALE",
        "version": "version_0",
        "url": [urljoin(u["base_url"], f"{rel}?download=1") for rel in selected],
        "local_path": [str(raw / "ukdale" / rel) for rel in selected],
        "sha256": "",
        "source_bytes": [sizes[rel] for rel in selected],
        "house": u["house"],
        "start": [file_start_ns(rel) / 1e9 for rel in selected],
        "end": "",
        "calibration_status": "to_download",
    })
    man.mkdir(parents=True, exist_ok=True)
    df.to_csv(man / "ukdale_all.csv", index=False)
    if not _covers_lots(selected, sizes, targets, min_ratio=min_ratio):
        total = sum(sizes[f] for f in selected)
        print(
            f"Listed and sized {len(selected)} of at most {max_files} files "
            f"({total / 2**30:.2f} GiB); not enough yet for all configured lots. "
            "Add weeks or raise --max-files, then rerun."
        )
    return df


def debug_listing(cfg: dict, week: str) -> None:
    u = cfg["ukdale"]
    url = urljoin(u["list_base_url"], f"{u['house']}/{week.strip('/')}/")
    response = request_with_retry("get", url, headers=HDR, timeout=60)
    print(f"HTTP status: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Content-Type: {response.headers.get('Content-Type', '')}")
    print("Page preview (first 800 characters):")
    print(response.text[:800])


def download_lots(cfg: dict, lots: list[str], dry_run: bool = False) -> None:
    raw, man = resolve(cfg, "data_raw"), resolve(cfg, "manifests")
    u = cfg["ukdale"]
    cal = raw / "ukdale" / u["calibration_file"]
    download(urljoin(u["base_url"], u["calibration_file"]) + "?download=1", cal, cfg["paths"]["min_free_disk_gb"], dry_run=dry_run)
    allm = pd.read_csv(man / "ukdale_all.csv", dtype={"sha256": str})
    for lot in lots:
        ldf = pd.read_csv(man / "lots" / f"{lot}.csv")
        for _, r in ldf.iterrows():
            row = allm.index[allm.local_path == r.local_path][0]
            url = allm.at[row, "url"]
            p = Path(r.local_path)
            download(url, p, cfg["paths"]["min_free_disk_gb"], dry_run=dry_run)
            if not dry_run:
                allm.at[row, "sha256"] = sha256_file(p)
                allm.at[row, "calibration_status"] = "cfg_downloaded"
        allm.to_csv(man / "ukdale_all.csv", index=False)
        print(f"lot {lot}: {len(ldf)} files, free disk {free_gb(raw):.1f} GB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["metropt", "ukdale-list", "ukdale-download", "ukdale-debug"])
    ap.add_argument("--weeks", nargs="*", help="e.g. 2013/wk11 2013/wk12")
    ap.add_argument("--week", help="single week for ukdale-debug, e.g. 2013/wk11")
    ap.add_argument("--filelist", type=Path)
    ap.add_argument("--lots", nargs="*")
    ap.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    if a.cmd == "metropt":
        print(acquire_metropt(cfg, a.dry_run))
    elif a.cmd == "ukdale-list":
        df = build_ukdale_manifest(cfg, a.weeks, a.filelist, a.max_files)
        print(len(df), "files,", df.source_bytes.sum() / 2**30, "GB listed")
    elif a.cmd == "ukdale-debug":
        if not a.week:
            ap.error("ukdale-debug requires --week")
        debug_listing(cfg, a.week)
    else:
        download_lots(cfg, a.lots, a.dry_run)
