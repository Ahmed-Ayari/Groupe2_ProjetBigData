"""SYNTHETIC data generators, used ONLY by tests and smoke runs. Never reported as results."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf

VOLTS_PER_STEP = 230.0 * np.sqrt(2) / 2_000_000      # so a 230 V RMS sine uses ~2e6 ADC steps
AMPS_PER_STEP = 10.0 * np.sqrt(2) / 2_000_000


def write_calibration(path: Path) -> None:
    path.write_text(f"[Calibration]\nvolts_per_adc_step = {VOLTS_PER_STEP}\namps_per_adc_step = {AMPS_PER_STEP}\n")


def write_flac(path: Path, start_s: int, micro: int = 0, seconds: float = 30.0, rate: int = 16000,
               seed: int = 0, i_amp: float = 5.0) -> Path:
    """24-bit stereo FLAC: ch0 voltage, ch1 current (known ground truth)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    t = np.arange(n) / rate
    u = 230 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t)
    i = i_amp * (1 + 0.3 * np.sin(2 * np.pi * t / 7)) * np.sqrt(2) * np.sin(2 * np.pi * 50 * t - 0.3) + rng.normal(0, 0.05, n)
    adc = np.stack([u / VOLTS_PER_STEP, i / AMPS_PER_STEP], axis=1).round().astype(np.int32)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = path.parent / f"vi{start_s}_{micro}.flac"
    # soundfile int32 writes are left-justified into 24 bits: pre-shift by 8 so decoded raw / 256 = adc
    sf.write(str(out), adc * 256, rate, subtype="PCM_24", format="FLAC")
    return out


def make_metropt_csv(path: Path, hours: float = 6.0, step_s: float = 10.0, start="2020-04-01 00:00:00", seed: int = 0) -> Path:
    rng = np.random.default_rng(seed)
    n = int(hours * 3600 / step_s)
    ts = pd.date_range(start, periods=n, freq=f"{int(step_s)}s")
    df = pd.DataFrame({
        "timestamp": ts,
        "TP2": rng.normal(0, 0.5, n) + 5, "TP3": rng.normal(9, 0.2, n),
        "Oil_temperature": 60 + 5 * np.sin(np.arange(n) / 500) + rng.normal(0, 0.4, n),
        "Motor_current": np.where(rng.random(n) < 0.4, rng.normal(4, 0.3, n), 0.04),
        "COMP": (rng.random(n) < 0.5).astype(float),
    })
    df = df.drop(index=range(n // 3, n // 3 + 40))   # a gap, to exercise missing windows
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
