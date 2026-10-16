"""Calls S5's reasoning code (src/reasoning) on an in-memory S4 graph.

S5's files use flat imports (``from verifier import ...``), so they are loaded from their own
folder instead of being imported as a package. Nothing in src/reasoning is modified: S7 only
swaps the graph source (the live S4 graph instead of a file) and, when no Ollama server is
running, the parser.
"""

import importlib.util
import sys
from pathlib import Path

from . import rule_parser

S5_DIR = Path(__file__).resolve().parents[1] / "reasoning"
_main = None


def _load_s5():
    global _main
    if _main is None:
        if str(S5_DIR) not in sys.path:
            sys.path.insert(0, str(S5_DIR))
        spec = importlib.util.spec_from_file_location("s5_main", S5_DIR / "main.py")
        _main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_main)
    return _main


def ollama_available() -> bool:
    try:
        import ollama

        ollama.list()
        return True
    except Exception:  # not installed, server not running, wrong host...
        return False


def resolve_parser(mode: str = "auto") -> str:
    """'ollama' | 'rules' | 'auto' -> the parser that will actually be used."""
    if mode == "auto":
        return "ollama" if ollama_available() else "rules"
    return mode


def answer(question: str, graph: dict, parser: str = "rules") -> dict:
    """Run S5's ``answer_question`` against ``graph``. Returns S5's ReasoningResult + ``parser``."""
    s5 = _load_s5()
    original = s5.parse_query, s5.load_graph
    try:
        s5.load_graph = lambda *a, **k: graph
        if parser == "rules":
            normalize = sys.modules["query_parser"]._normalize   # S5's own clean-up step
            s5.parse_query = lambda q: normalize(rule_parser.parse_query(q))
        result = s5.answer_question(question)
    finally:
        s5.parse_query, s5.load_graph = original
    result["parser"] = parser
    return result
