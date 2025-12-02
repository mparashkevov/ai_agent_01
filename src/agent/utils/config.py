import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    agent_base_dir: str
    debug: bool = False


def get_config() -> Config:
    base = os.getenv("AGENT_BASE_DIR", ".")
    debug = os.getenv("AGENT_DEBUG", "0") in ("1", "true", "True")
    # Normalize
    base = os.path.abspath(base)
    return Config(agent_base_dir=base, debug=debug)
