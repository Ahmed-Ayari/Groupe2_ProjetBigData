"""UK-DALE helpers: calibration parsing, filename timestamps, block decoding, per-file partials.

Nothing here is assumed silently: channel order, int scaling and timestamps have explicit
verification (`verify`) because wrong assumptions give plausible but wrong numbers.
"""
from __future__ import annotations
import argparse
import configparser
import re
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf

from .config import load_config
from . import windows as W

FNAME = re.compile(r"vi(\d+)_(\d+)\.flac$")


@dataclass(frozen=True)
class Calibration:
    volts_per_adc_step: float
    amps_per_adc_step: float


def parse_calibration(path: str | Path) -> Calibration:
    """Parse calibration_house_N.cfg (ini style). Keys are looked up by name, not position."""
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    flat = {k.lower(): v for s in cp.sections() for k, v in cp.items(s)}
    try:
        return Calibration(float(flat["volts_per_adc_step"]), float(flat["amps_per_adc_step"]))
    except KeyError as exc:  # fail loudly: document the cfg content instead of guessing
        raise KeyError(f"calibration keys not found in {path}: {sorted(flat)}") from exc


def file_start_ns(path: str | Path) -> int:
    """Start time from filename vi<epoch_s>_<microseconds>.flac (to be verified against sample count)."""
    m = FNAME.search(str(path))
    if not m:
        raise ValueError(f"unexpected UK-DALE filename: {path}")
    return int(m.group(1)) * W.NS + int(m.group(2)) * 1000


def shift_bits(path: str | Path, setting: str | int) -> int:
    if setting != "auto":
        return int(setting)
    return 8 if sf.info(str(path)).subtype == "PCM_24" else 0


def file_partials(path: str | Path, cal: Calibration, w_s: float, block_seconds: float = 60.0,
                  channel_order: tuple[str, str] = ("voltage", "current"),
                  int_shift_bits: str | int = "auto") -> pd.DataFrame:
    """Decode one FLAC by blocks and return compact merged partial sums per window.

    Peak memory is one block, not the file. Used by B0 (local) AND by Spark workers (mapInPandas).
    """
    path = str(path)
    info = sf.info(path)
    rate = info.samplerate
    if info.channels != 2:
        raise ValueError(f"{path}: expected 2 channels, got {info.channels}")
    sh = shift_bits(path, int_shift_bits)
    iu, ii = (0, 1) if channel_order[0] == "voltage" else (1, 0)
    start = file_start_ns(path)
    step_ns = W.NS // rate if W.NS % rate == 0 else None
    block = int(rate * block_seconds)
    pos = 0
    parts = []
    for data in sf.blocks(path, blocksize=block, dtype="int32", always_2d=True):
        n = data.shape[0]
        raw = data.astype(np.float64) / (2 ** sh if sh else 1)
        u = raw[:, iu] * cal.volts_per_adc_step
        i = raw[:, ii] * cal.amps_per_adc_step
        idx = np.arange(pos, pos + n, dtype=np.int64)
        t_ns = start + (idx * step_ns if step_ns else np.round(idx * (W.NS / rate)).astype(np.int64))
        parts.append(W.uk_block_partials(u, i, t_ns, w_s))
        pos += n
    if not parts:
        return pd.DataFrame(columns=["window_id", *W.UK_SUMS, "max_i"])
    return W.uk_merge(pd.concat(parts, ignore_index=True))


def verify(path: str, cfg: dict, cal: Calibration) -> dict:
    """Evidence for channel order / scaling: calibrated voltage RMS must be near mains (~230 V)."""
    info = sf.info(path)
    out = {"file": path, "samplerate": info.samplerate, "channels": info.channels,
           "subtype": info.subtype, "frames": info.frames, "duration_s": info.frames / info.samplerate,
           "start_ns_from_name": file_start_ns(path)}
    data, _ = sf.read(path, frames=info.samplerate * 5, dtype="int32", always_2d=True)
    sh = shift_bits(path, cfg["ukdale"]["int_shift_bits"])
    raw = data.astype(np.float64) / (2 ** sh if sh else 1)
    for name, ch in (("ch0", 0), ("ch1", 1)):
        out[f"{name}_rms_raw"] = float(np.sqrt(np.mean(raw[:, ch] ** 2)))
        out[f"{name}_rms_if_voltage"] = out[f"{name}_rms_raw"] * cal.volts_per_adc_step
        out[f"{name}_rms_if_current"] = out[f"{name}_rms_raw"] * cal.amps_per_adc_step
    out["voltage_channel_guess"] = "ch0" if abs(out["ch0_rms_if_voltage"] - 230) < abs(out["ch1_rms_if_voltage"] - 230) else "ch1"
    out["configured_order"] = cfg["ukdale"]["channel_order"]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify"])
    ap.add_argument("file")
    ap.add_argument("--cal", required=True)
    a = ap.parse_args()
    import json
    print(json.dumps(verify(a.file, load_config(), parse_calibration(a.cal)), indent=2, default=str))
