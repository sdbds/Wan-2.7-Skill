from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from typing import Any
from urllib import error, parse, request


def _guess_extension(url: str, content_type: str | None, *, default: str) -> str:
    suffix = Path(parse.urlparse(url).path).suffix.lower()
    if suffix:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return default


def download_urls(
    urls: list[str],
    *,
    output_dir: Path,
    stem: str,
    default_extension: str,
    timeout: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    local_paths: list[str] = []
    failures: list[dict[str, Any]] = []

    for index, url in enumerate(urls, start=1):
        file_path: Path | None = None
        try:
            with request.urlopen(url, timeout=timeout) as response:
                extension = _guess_extension(
                    url,
                    response.headers.get("Content-Type"),
                    default=default_extension,
                )
                file_path = output_dir / f"{stem}-{index:02d}{extension}"
                with file_path.open("wb") as output_file:
                    shutil.copyfileobj(response, output_file, length=1024 * 1024)
                local_paths.append(str(file_path.resolve()))
        except (error.URLError, OSError) as exc:
            if file_path is not None:
                file_path.unlink(missing_ok=True)
            failures.append({"url": url, "message": str(exc)})

    return local_paths, failures
