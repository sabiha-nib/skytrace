"""The browser's deterministic ZIP writer (session packages) produces archives Python reads, with valid CRCs and
identical bytes for identical inputs."""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_zipstore_output_is_valid_and_deterministic(tmp_path):
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    subprocess.run([NODE, str(ROOT / "tests/js/zip_out.mjs"), str(ROOT), str(a), str(b)], check=True, timeout=60)
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as z:
        assert z.testzip() is None
        assert z.namelist() == ["pkg/a.txt", "pkg/b.bin", "pkg/empty.txt"]
        assert z.read("pkg/a.txt").decode() == "hello µ 😀\n"
        assert z.read("pkg/b.bin") == bytes([0, 1, 2, 255, 254])
        assert z.read("pkg/empty.txt") == b""
        assert all(i.date_time == (2020, 1, 1, 0, 0, 0) and i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
