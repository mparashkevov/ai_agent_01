import os
from typing import Tuple, Optional, List

from ..utils.config import get_config
from ..tools.ollama_tool import generate as ollama_generate

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


def _collect_texts_from_dir(dirpath: str, max_file_size: int = 200 * 1024) -> List[str]:
    parts: List[str] = []
    for root, _, files in os.walk(dirpath):
        for fn in files:
            if fn.lower().endswith((".txt", ".md", ".rst", ".json", ".mdx")):
                p = os.path.join(root, fn)
                try:
                    size = os.path.getsize(p)
                    if size > max_file_size:
                        continue
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        parts.append(f"== {os.path.relpath(p, dirpath)} ==\n" + fh.read())
                except Exception:
                    continue
    return parts


def query_index(index_name: str = "default", query: str = "", top_k: int = 3, docs_path: Optional[str] = None) -> Tuple[bool, str]:
    """Query a previously saved index.<index_name>.json and return textual result.

    If `OLLAMA_URL` is set in the environment, this will fall back to using local Ollama
    to answer the question using documents from `docs_path` (relative to AGENT_BASE_DIR).
    """
    # Prefer Ollama local runtime if configured
    ollama_url = os.getenv("OLLAMA_URL")
    if ollama_url:
        docs_path = docs_path or "."
        docs_full = os.path.normpath(os.path.join(cfg.agent_base_dir, docs_path))
        if not docs_full.startswith(cfg.agent_base_dir):
            return False, "Access denied to docs path"

        parts = _collect_texts_from_dir(docs_full)
        context = "\n\n---\n\n".join(parts[:50])
        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:" if context else f"Question: {query}\nAnswer:"
        ok, out = ollama_generate(prompt, model=os.getenv("OLLAMA_MODEL"))
        return ok, out

    # Fallback to llama-index if available
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
