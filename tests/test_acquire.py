from pathlib import Path

from bigdata import acquire


ROOT = Path(__file__).resolve().parents[1]


def test_parse_listing_fixture():
    html = (ROOT / "tests" / "fixtures" / "ukdale_listing.html").read_text(encoding="utf-8")
    assert acquire.parse_listing(html) == [
        "https://dap.ceda.ac.uk/edc/d1/887733b3-4c04-471f-9404-9f7459c4a1a0/data/version_0/house_1/2013/wk11/vi-1363392000_236972.flac?download=1",
        "../",
        "index.html",
    ]
    assert acquire._week_files(
        html,
        "https://data.ceda.ac.uk/edc/d1/887733b3-4c04-471f-9404-9f7459c4a1a0/data/version_0/house_1/2013/wk11/",
        "house_1",
        "2013/wk11",
    ) == ["house_1/2013/wk11/vi-1363392000_236972.flac"]


def test_file_start_ns_accepts_ceda_hyphenated_filename():
    assert acquire.file_start_ns("vi-1363392000_236972.flac") == 1363392000 * 10**9 + 236972 * 1000


def test_listing_coverage_includes_realized_ratio_expansion():
    cfg = acquire.load_config(ROOT / "configs" / "default.yaml")
    targets = acquire._lot_targets(cfg)
    file_bytes = int(0.2 * 2**30)
    files = [f"f{i}" for i in range(100)]
    sizes = {name: file_bytes for name in files}
    assert not acquire._covers_lots(files[:30], sizes, targets, min_ratio=4)
    assert acquire._covers_lots(files, sizes, targets, min_ratio=4)


def test_list_dir_retries_503_then_succeeds(monkeypatch):
    class Response:
        def __init__(self, status_code, headers, text):
            self.status_code = status_code
            self.headers = headers
            self.text = text

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    responses = iter([
        Response(503, {"Retry-After": "0"}, "unavailable"),
        Response(200, {}, "<a href='example.flac'>file</a>"),
    ])
    requests_seen = []
    sleeps = []

    def fake_get(url, **kwargs):
        requests_seen.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr(acquire.requests, "get", fake_get)
    monkeypatch.setattr(acquire.time, "sleep", sleeps.append)

    page = acquire.list_dir("https://data.ceda.ac.uk/week/")

    assert "example.flac" in page
    assert len(requests_seen) == 2
    assert requests_seen[0][1]["headers"] == acquire.HDR
    assert sleeps == [0.0]
