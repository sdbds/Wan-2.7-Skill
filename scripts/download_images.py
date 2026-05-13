from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from urllib import error, parse, request


def _guess_extension(url: str, content_type: str | None) -> str:
    path = parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".png"


def download_images(
    image_urls: list[str],
    *,
    output_dir: Path,
    timeout: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    local_paths: list[str] = []
    failures: list[dict[str, Any]] = []

    for index, image_url in enumerate(image_urls, start=1):
        try:
            with request.urlopen(image_url, timeout=timeout) as response:
                content = response.read()
                extension = _guess_extension(
                    image_url, response.headers.get("Content-Type")
                )
                file_path = output_dir / f"image-{index:02d}{extension}"
                file_path.write_bytes(content)
                local_paths.append(str(file_path.resolve()))
        except (error.URLError, OSError) as exc:
            failures.append({"url": image_url, "message": str(exc)})

    return local_paths, failures
