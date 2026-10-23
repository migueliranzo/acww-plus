#!/usr/bin/env python3
"""Runs every headless test against build/acww_plus.nds (sequentially: they share an emulator port) and prints
the RESULT lines. usage: py -3.12 tools/run_all_tests.py [--release] [--region eu|us]
--release: against build/acww_plus_release.nds (tools/build_rom.py --release); the sitting and lamp-switching
tests are replaced by checks that those features are off.
--region us: against the US build (build/us/, tools/build_rom.py --region us), with the US test save."""
import os
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).parent
TESTS = [
    ["test_furniture.py", "collide", "drop"],
    ["test_furniture.py", "marker"],
    ["test_furniture.py", "house"],
    ["test_furniture.py", "ghost"],
    ["test_furniture.py", "treedrop"],
    ["test_furniture.py", "lampuse", "night"],
    ["test_furniture.py", "lampuse", "day"],
    ["test_furniture.py", "sit", "chair"],
    ["test_furniture.py", "sit", "bench"],
    ["test_code_home.py"],
    ["test_tool_swap.py"],
    ["test_tree_shake.py"],
    ["test_skin_tone.py"],
    ["test_pattern_alpha.py", "plus"],
    ["test_look_persist.py"],
]


RELEASE_OFF = {("test_furniture.py", "sit"), ("test_furniture.py", "lampuse")}


def main():
    summary = []
    tests = TESTS
    region = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "eu"
    os.environ["ACWW_REGION"] = region
    build = T.parent / "build" if region == "eu" else T.parent / "build" / region
    if "--release" in sys.argv:
        os.environ["ACWW_ROM"] = str(build / "acww_plus_release.nds")
        tests = [t + ["off"] if tuple(t[:2]) in RELEASE_OFF else t for t in TESTS]
        tests = [t for t in tests if not (tuple(t[:2]) in RELEASE_OFF and t[2] in ("bench", "day"))]
    for t in tests:
        t0 = time.time()
        r = subprocess.run([sys.executable, str(T / t[0])] + t[1:], capture_output=True, text=True)
        lines = [l.strip() for l in r.stdout.splitlines() if "RESULT" in l]
        if r.returncode != 0:
            lines.append(f"RESULT {' '.join(t)}: CRASH (exit {r.returncode}) {r.stderr.strip().splitlines()[-1:]}")
        dt = time.time() - t0
        print(f"== {' '.join(t)} ({dt:.0f}s)")
        for l in lines:
            print("  " + l)
        summary += lines
    fails = [l for l in summary if "PASS" not in l]
    print(f"\n{len(summary) - len(fails)} pass, {len(fails)} not pass")
    for l in fails:
        print("  " + l)


if __name__ == "__main__":
    main()
