"""Compares local models on the same 7 questions (PASS/FAIL + seconds). No scene graph needed.
Run: python3 test_parser.py [model]   e.g. python3 test_parser.py qwen2.5:3b
"""

import sys
import time

from query_parser import parse_query

CASES = [
    ("Which chair is closest to the mug?", "chair", "mug", ""),
    ("Which free chair is closest to the lidar scanner?", "chair", "scanner", ""),
    ("Find a chair that is not near the laptop", "chair", "", "laptop"),
    ("Where is the red mug?", "mug", "", ""),
    ("What is closest to the laptop?", "", "laptop", ""),
    ("Find the cup that is not near the laptop", "cup", "", "laptop"),
    ("Find the book that is not near the mug", "book", "", "mug"),
]


def check(parsed, target, reference, excluded):
    if "error" in parsed:
        return False
    negatives = parsed.get("negative_constraints", [])
    excluded_ok = any(excluded in str(n.get("object", "")).lower() for n in negatives) if excluded else not negatives
    return (
        target in str(parsed.get("target", "")).lower()
        and (reference in str(parsed.get("reference", "")).lower() if reference else not parsed.get("reference"))
        and excluded_ok
    )


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else None
    passed, times = 0, []
    for question, target, reference, excluded in CASES:
        start = time.time()
        parsed = parse_query(question, model=model)
        seconds = time.time() - start
        times.append(seconds)
        ok = check(parsed, target, reference, excluded)
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {seconds:4.1f}s  {question}")
        if not ok:
            print(f"        -> {parsed}")
    avg = sum(times[1:]) / len(times[1:])
    print(f"\nModel: {model or 'default'} | {passed}/{len(CASES)} passed | avg {avg:.1f}s (first call excluded)")
    sys.exit(0 if passed == len(CASES) else 1)
