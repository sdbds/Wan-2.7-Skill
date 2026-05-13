from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import download_media


class FakeResponse:
    def __init__(self, chunks: list[bytes], read_sizes: list[int]):
        self._chunks = list(chunks)
        self._read_sizes = read_sizes
        self.headers = {"Content-Type": "video/mp4"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int = -1) -> bytes:
        self._read_sizes.append(size)
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_download_urls_streams_to_disk(monkeypatch, tmp_path: Path):
    read_sizes: list[int] = []

    def fake_urlopen(url: str, timeout: float):
        assert url == "https://example.com/video"
        assert timeout == 10
        return FakeResponse([b"abc", b"def"], read_sizes)

    monkeypatch.setattr(download_media.request, "urlopen", fake_urlopen)

    local_paths, failures = download_media.download_urls(
        ["https://example.com/video"],
        output_dir=tmp_path,
        stem="video",
        default_extension=".mp4",
        timeout=10,
    )

    assert failures == []
    assert read_sizes[0] == 1024 * 1024
    assert Path(local_paths[0]).read_bytes() == b"abcdef"
