"""Configuration loading. One YAML file is the single source of truth."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]


def config_path() -> Path:
    p = Path(os.environ.get("BIGDATA_CONFIG", ROOT / "configs" / "default.yaml"))
    return p if p.is_absolute() else ROOT / p


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    with open(path or config_path(), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve(cfg: dict[str, Any], key: str) -> Path:
    """Resolve a path from cfg['paths'][key] relative to the repo root."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else ROOT / p


def tol(cfg: dict[str, Any], name: str = "default") -> tuple[float, float]:
    t = cfg["tolerances"].get(name, cfg["tolerances"]["default"])
    return float(t["atol"]), float(t["rtol"])
