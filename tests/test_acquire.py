from pathlib import Path

from bigdata import acquire


ROOT = Path(__file__).resolve().parents[1]


def test_parse_listing_fixture():
    html = (ROOT / "tests" / "fixtures" / "ukdale_listing.html").read_text(encoding="utf-8")
    assert acquire.parse_listing(html) == ["example.flac", "../", "index.html"]


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
