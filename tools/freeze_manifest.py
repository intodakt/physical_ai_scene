"""W15 freeze (professor's guide §15, Appendix C "all thresholds/configurations/prompts are frozen and versioned").

    python tools/freeze_manifest.py              # write configs/FROZEN_MANIFEST.json (SHA-256 of every config)
    python tools/freeze_manifest.py --check      # exit 1 if any frozen file changed since the freeze

Freeze once after the dev-split tuning (S4 NEAR sweep, S2 / S3 configs) and before the final test runs.
Commit the manifest; every final result is then reproducible from the listed files and the git commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs" / "FROZEN_MANIFEST.json"
PATTERNS = ["configs/**/*.yaml", "configs/**/*.yml", "configs/**/*.json", "src/open_vocab/configs/**/*",
            "src/reasoning/query_parser.py", "src/scene_graph/rules.py", "eval/dataset/splits.json", "requirements.txt"]
OWNER = {"configs/fusion_3d.yaml": "S2", "configs/s4_frozen.yaml": "S4", "src/open_vocab/configs": "S3",
         "src/reasoning/query_parser.py": "S5 (LLM prompt + model)", "src/scene_graph/rules.py": "S4 (relation thresholds)",
         "configs/sensors": "S1", "configs/s7_integration.yaml": "S7 (pipeline, tracking, action)", "eval/dataset/splits.json": "S1",
         "requirements.txt": "S7"}


def files() -> list[Path]:
    seen = set()
    for pat in PATTERNS:
        for p in sorted(ROOT.glob(pat)):
            if p.is_file() and p.name != OUT.name and p not in seen:
                seen.add(p)
    return sorted(seen)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def owner(rel: str) -> str:
    return next((v for k, v in OWNER.items() if rel == k or rel.startswith(k + "/")), "")


def build() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    entries = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "owner": owner(p.relative_to(ROOT).as_posix())} for p in files()]
    return {"frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": commit, "files": entries}


def check(manifest: dict) -> list[str]:
    problems = []
    for e in manifest["files"]:
        p = ROOT / e["path"]
        if not p.exists():
            problems.append(f"missing: {e['path']}")
        elif sha(p) != e["sha256"]:
            problems.append(f"changed after the freeze: {e['path']} ({e['owner']})")
    new = {p.relative_to(ROOT).as_posix() for p in files()} - {e["path"] for e in manifest["files"]}
    problems += [f"new, not in the freeze: {n}" for n in sorted(new)]
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        if not OUT.exists():
            print("no freeze yet: run python tools/freeze_manifest.py")
            sys.exit(1)
        problems = check(json.loads(OUT.read_text()))
        for p in problems:
            print("x", p)
        print("OK: frozen configuration unchanged" if not problems else f"{len(problems)} problem(s)")
        sys.exit(1 if problems else 0)
    m = build()
    OUT.write_text(json.dumps(m, indent=2) + "\n")
    print(f"froze {len(m['files'])} files at commit {m['git_commit'][:8]} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
