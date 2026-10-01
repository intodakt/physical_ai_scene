"""
S5 - Model comparison test
---------------------------
Runs the same questions through a local model and checks whether the
parsed JSON has the right target / reference. Use it to compare models.

Run:
    python test_parser.py                 # uses default model (qwen3:8b)
    python test_parser.py llama3.1:8b     # try another model
"""

import sys
import time

from parser import parse_query

# (question, expected target word, expected reference word, expects negative constraint)
CASES = [
    ("Which chair is closest to the mug?", "chair", "mug", False),
    ("Which free chair is closest to the lidar scanner?", "chair", "scanner", False),
    ("Find a chair that is not near the laptop", "chair", "", True),
    ("Where is the red mug?", "mug", "", False),
    ("What is closest to the laptop?", "", "laptop", False),
    ("Find the cup that is not near the laptop", "cup", "", True),
]


def check(parsed: dict, target: str, reference: str, neg: bool) -> bool:
    if "error" in parsed:
        return False
    got_target = str(parsed.get("target", "")).lower()
    got_ref = str(parsed.get("reference", "")).lower()
    got_neg = bool(parsed.get("negative_constraints"))
    ok_target = (target in got_target) if target else True
    ok_ref = (reference in got_ref) if reference else True
    return ok_target and ok_ref and (got_neg == neg)


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else None
    passed = 0
    for question, target, reference, neg in CASES:
        start = time.time()
        parsed = parse_query(question, model=model)
        secs = time.time() - start
        ok = check(parsed, target, reference, neg)
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {secs:4.1f}s  {question}")
        print(f"        -> {parsed}")
    print(f"\nModel: {model or 'default'}  |  {passed}/{len(CASES)} passed")
