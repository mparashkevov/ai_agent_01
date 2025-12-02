import os
from typing import Tuple

from ..utils.config import get_config

cfg = get_config()


def _abs_path_relaxed(path: str) -> str:
    # normalize and join to base to avoid path escapes
    base = cfg.agent_base_dir
    joined = os.path.normpath(os.path.join(base, path))
    return joined


def read_file(path: str, encoding: str = "utf-8") -> Tuple[bool, str]:
    """Read a file relative to `AGENT_BASE_DIR`. Returns (success, content_or_error)."""
    try:
        abs_path = _abs_path_relaxed(path)
        if not abs_path.startswith(os.path.normpath(cfg.agent_base_dir)):
            return False, "Access denied"
        with open(abs_path, "r", encoding=encoding) as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)


def write_file(path: str, content: str, encoding: str = "utf-8") -> Tuple[bool, str]:
    try:
        abs_path = _abs_path_relaxed(path)
        if not abs_path.startswith(os.path.normpath(cfg.agent_base_dir)):
            return False, "Access denied"
        dirpath = os.path.dirname(abs_path)
        os.makedirs(dirpath, exist_ok=True)
        with open(abs_path, "w", encoding=encoding) as f:
            f.write(content)
        return True, "written"
    except Exception as e:
        return False, str(e)
