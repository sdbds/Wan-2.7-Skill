from __future__ import annotations

import os
from pathlib import Path


class ApiKeyNotFoundError(RuntimeError):
    """Raised when no usable API key source can be found."""


def load_api_key(workspace_root: Path) -> tuple[str, str]:
    workspace_candidate = workspace_root / "api_key.txt"
    if workspace_candidate.is_file():
        value = workspace_candidate.read_text(encoding="utf-8").strip()
        if value:
            return value, str(workspace_candidate)

    env_value = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if env_value:
        return env_value, "env:DASHSCOPE_API_KEY"

    raise ApiKeyNotFoundError(
        "No API key found. Provide <workspace>/api_key.txt or set DASHSCOPE_API_KEY."
    )
