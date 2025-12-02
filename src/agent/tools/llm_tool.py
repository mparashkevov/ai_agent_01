import os
from typing import Tuple, Optional

from ..utils.config import get_config

cfg = get_config()

# Try importing llama-index; provide helpful error if not installed.
try:
    from llama_index import SimpleDirectoryReader, GPTVectorStoreIndex
    _LLM_AVAILABLE = True
    _LLM_ERR = None
except Exception as e:
    SimpleDirectoryReader = None  # type: ignore
    GPTVectorStoreIndex = None  # type: ignore
    _LLM_AVAILABLE = False
    _LLM_ERR = str(e)


def build_index(index_name: str = "default", docs_path: Optional[str] = None) -> Tuple[bool, str]:
    """Build a simple vector index from documents under `docs_path` (relative to AGENT_BASE_DIR).

    Saves the index as `<index_name>.json` in `AGENT_BASE_DIR`.
    """
    if not _LLM_AVAILABLE:
        return False, f"llama-index not available: {_LLM_ERR}"

    docs_path = docs_path or "."
    docs_full = os.path.normpath(os.path.join(cfg.agent_base_dir, docs_path))
    if not docs_full.startswith(cfg.agent_base_dir):
        return False, "Access denied to docs path"

    try:
        docs = SimpleDirectoryReader(docs_full).load_data()
        index = GPTVectorStoreIndex.from_documents(docs)
        index_file = os.path.join(cfg.agent_base_dir, f"{index_name}.json")
        index.save_to_disk(index_file)
        return True, index_file
    except Exception as e:
        return False, str(e)


def query_index(index_name: str = "default", query: str = "", top_k: int = 3) -> Tuple[bool, str]:
    """Query a previously saved index.<index_name>.json and return textual result."""
    if not _LLM_AVAILABLE:
        return False, f"llama-index not available: {_LLM_ERR}"

    index_file = os.path.join(cfg.agent_base_dir, f"{index_name}.json")
    if not os.path.exists(index_file):
        return False, "index file not found"

    try:
        index = GPTVectorStoreIndex.load_from_disk(index_file)
        qe = index.as_query_engine()
        res = qe.query(query)
        return True, str(res)
    except Exception as e:
        return False, str(e)
