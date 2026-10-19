"""Statistical PC profile of the ARM9 in town: stop every N retired instructions, bucket the PC
(payload functions from build/payload.map, otherwise by module). usage: pc_profile.py vanilla|plus port [stride]"""
import bisect, collections, sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
which, port = sys.argv[1], int(sys.argv[2])
stride = int(sys.argv[3]) if len(sys.argv) > 3 else 997
save = prepare_save(PROJECT / "build" / f"probe_pc_{which}.sav")
syms = sorted((a, n) for n, a in payload_symbols().items())
addrs = [a for a, _ in syms]
with Emu(ROM_VANILLA if which == "vanilla" else ROM_PLUS, str(save), port=port, tag=f"pc_{which}") as e:
    e.boot_to_town(); e.wait(400)
    walk_until(e, "down", 2, 59.0, max_frames=200)
    e.wait(200)
    cnt = collections.Counter(); total = 0
    for i in range(6000):
        ic = e.c.cmd("event_counts")["insn9"]
        e.c.cmd("run_to_event", event="insn9", count=ic + stride, stall=2000)
        pc = e.regs()["r"][15]
        if 0x01FFDC00 <= pc < 0x02000000 and which == "plus":
            k = bisect.bisect_right(addrs, pc) - 1
            cnt["payload:" + (syms[k][1] if k >= 0 else "?")] += 1
        elif pc < 0x02000000: cnt["itcm/bios"] += 1
        elif pc < 0x020E8180: cnt["main"] += 1
        elif pc < 0x02207F60: cnt["autoload2 (SDK)"] += 1
        else: cnt["overlays"] += 1
        total += 1
    for k, v in cnt.most_common(20):
        print(f"  {k:40s} {100.0*v/total:5.1f}%")
