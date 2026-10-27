#!/usr/bin/env python3
"""item_value hook (src/heap/fruit_stack.c): check the patched entry and the moved instructions in the built ROM,
then break on the hook in play and report what each call returns.
usage: item_value_probe.py"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from harness import *  # noqa

heap = {l.split()[1]: int(l.split()[0], 16) for l in (BUILD / "heap.map").read_text().split("\n") if l.strip()}
HOOK = heap["hook_item_value"]
pokes = {0xC + 0x1B22 + 2 * i: 0xFFF1 for i in range(15)}
pokes[0xC + 0x1B22] = 0x156F          # 3 apples
pokes[0xC + 0x1B22 + 2] = 0x1518      # 1 apple
pokes[0xC + 0x1B22 + 4] = 0x149B      # 1,000 Bells
save = prepare_save(BUILD / "probe_item_value.sav", pokes=pokes)
with Emu(ROM_PLUS, str(save), tag="item_value") as e:
    e.boot_to_town()
    print("  entry:", e.read(0x0204BF98, 8).hex(), " moved:", e.read(heap["s_item_value_orig"], 16).hex())
    e.wait(100)
    e.press("y", hold=6, after=120)
    e.press("right", hold=6, after=30)
    e.press("right", hold=6, after=30)
    e.press("a", hold=6, after=60)        # the bag's menu
    e.shot("bag_menu")
    e.press("a", hold=6)
    seen = {}
    for _ in range(40):
        r = e.run_to_pc(HOOK, timeout_frames=120)
        print("  run_to_pc:", r)
        if not r.get("reached") or "error" in r:
            break
        regs = e.regs()["r"]
        item, lr = e.u16(regs[0]), regs[14]
        r2 = e.run_to_pc(lr & ~1, timeout_frames=10)
        val = e.regs()["r"][0]
        seen.setdefault(item, set()).add(val)
        if len(seen) >= 4:
            break
    for item, vals in seen.items():
        print(f"  item_value({item:#06x}) = {sorted(vals)}")
    if not seen:
        print("  no item_value call seen")
