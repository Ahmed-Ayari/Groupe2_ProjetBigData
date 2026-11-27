import subprocess

from bigdata import runner


def test_code_version_tracks_only_selected_file_contents(tmp_path, monkeypatch):
    root = tmp_path
    (root / "src" / "bigdata").mkdir(parents=True)
    (root / "configs").mkdir()
    (root / "scripts").mkdir()
    (root / "src" / "bigdata" / "module.py").write_text("value = 1\n")
    (root / "configs" / "default.yaml").write_text("setting: true\n")
    (root / "scripts" / "run.sh").write_text("#!/bin/sh\n")
    (root / "STATUS.md").write_text("status one\n")
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.delenv("BIGDATA_CODE_VERSION", raising=False)

    def git(*args):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("add", ".")
    git("commit", "-m", "initial")
    initial = runner.git_hash()
    assert len(initial) == 10

    (root / "STATUS.md").write_text("status changed\n")
    git("add", "STATUS.md")
    git("commit", "-m", "unrelated status update")
    assert runner.git_hash() == initial

    (root / "src" / "bigdata" / "module.py").write_text("value = 2\n")
    assert runner.git_hash() != initial

    monkeypatch.setenv("BIGDATA_CODE_VERSION", "pinned-version")
    assert runner.git_hash() == "pinned-version"
