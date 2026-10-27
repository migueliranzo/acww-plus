#!/usr/bin/env python3
"""Breaks in nook_daily_restock during the town load and prints which one-player check stops the sale-day code.
usage: nook_restock_probe.py [rom]"""
import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from harness import *  # noqa

PCS = [(0x020AE8A4, "residents counted (r0)"), (0x020AE8DC, "after the resident loop (r7 = skip)"),
       (0x020AE8E6, "remodel day bytes (r0 -> [3])"), (0x020AE8F0, "sale-day update called")]


def main():
    rom = sys.argv[1] if len(sys.argv) > 1 else ROM_PLUS
    save = prepare_save(BUILD / "probe_nook.sav", pokes={0x15DB4 + 0x50: 0x0118, 0xC + 0x21FC: 0x0200})
    with Emu(rom, str(save), tag="nookprobe") as e:
        e.run_to(600)
        e.tap(128, 48)
        e.run_to(3000)
        scn = json.load(open(LOAD_SAVE_SCN))
        pending = list(PCS)
        for act in scn["actions"]:
            if act["kind"] == "key":
                e.press(act["key"], hold=3)
                continue
            frames = int(act["frames"])
            start = e.v()
            while pending and e.v() < start + frames:
                pc, what = pending[0]
                r = e.run_to_pc(pc, timeout_frames=start + frames - e.v())
                if not r.get("reached", r.get("hit")):
                    break
                regs = e.regs()
                print(f"  v{e.v()} 0x{pc:08X} {what}: r0={regs.get('r0', regs)} r7={regs.get('r7')}")
                pending.pop(0)
            if e.v() < start + frames:
                e.wait(start + frames - e.v())
        print("  not reached:", [w for _, w in pending])


main()
