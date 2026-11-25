import os, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("BIGDATA_CONFIG", str(ROOT / "configs" / "smoke.yaml"))
from bigdata.config import load_config  # noqa: E402


@pytest.fixture(scope="session")
def cfg():
    return load_config(ROOT / "configs" / "smoke.yaml")
