"""S7 pull-request gatekeeper: run this on a branch before it is merged into main.

    python tools/check_contracts.py                 # all git-tracked files
    python tools/check_contracts.py src/scene_graph outputs/scene_graph

Checks the two rules of the Week-5 review guide:
  1. no hard-coded absolute paths in code or configs (/home/..., C:\\Users\\..., ~/...);
  2. every JSON file that looks like a module hand-over honours its contract
     (S3 observation, S2 objects, S4 scene graph, S5 reasoning result, S6 action goal).
Exit code 0 = mergeable, 1 = reject the PR and send the listed problems to its author.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integration.contracts import CHECKS, detect_kind  # noqa: E402

CODE = {".py", ".yaml", ".yml", ".json", ".sh", ".launch", ".toml", ".cfg", ".ini"}
ABS_PATH = re.compile(r"""["'](?:/home/|/Users/|/mnt/|/media/|/root/|[A-Za-z]:\\\\|[A-Za-z]:/|~/)[^"']*["']""")
SELF = Path(__file__).resolve()


def files(targets):
    """Explicit paths are walked; with no arguments only git-tracked files are checked (= what a PR merges)."""
    if not targets:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        yield from (ROOT / f for f in out.split("\0") if f)
        return
    for t in targets:
        t = Path(t) if Path(t).is_absolute() else ROOT / t
        if t.is_file():
            yield t.resolve()
        elif t.is_dir():
            yield from (p.resolve() for p in sorted(t.rglob("*")) if p.is_file() and "__pycache__" not in p.parts)


def check(targets) -> list[str]:
    problems = []
    for p in files(targets):
        rel = p.relative_to(ROOT).as_posix()
        if p.suffix not in CODE or p == SELF:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if ABS_PATH.search(line) and not line.lstrip().startswith("#"):
                problems.append(f"{rel}:{n}: absolute path - use a path relative to the repo root")
        if p.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                problems.append(f"{rel}: invalid JSON ({e})")
                continue
            kind = detect_kind(data)
            if kind:
                problems += [f"{rel}: [{kind}] {e}" for e in CHECKS[kind](data)]
    return problems


def main():
    targets = sys.argv[1:]
    problems = check(targets)
    for p in problems:
        print("  x", p)
    print(f"{'REJECT' if problems else 'OK'}: {len(problems)} problem(s) in {', '.join(targets) or 'tracked files'}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
