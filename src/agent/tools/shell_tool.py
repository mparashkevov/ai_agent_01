import os
import shlex
import subprocess
from typing import Tuple, List, Optional

from ..utils.config import get_config

cfg = get_config()


def _sanitize_args(cmd: str) -> List[str]:
    return shlex.split(cmd)


def run_command(cmd: str, timeout: int = 30, cwd: Optional[str] = None) -> Tuple[bool, dict]:
    """Run a shell command. `cwd` is interpreted relative to `AGENT_BASE_DIR` if provided."""
    try:
        if cwd:
            target_cwd = os.path.normpath(os.path.join(cfg.agent_base_dir, cwd))
            if not target_cwd.startswith(os.path.normpath(cfg.agent_base_dir)):
                return False, {"error": "Access denied for cwd"}
        else:
            target_cwd = None

        args = _sanitize_args(cmd)
        proc = subprocess.run(args, cwd=target_cwd, capture_output=True, text=True, timeout=timeout)
        return True, {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as e:
        return False, {"error": str(e)}
