"""Game frames per 300 vblanks indoors (player's house) vs town, plus ARM9 idle."""
import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
save = prepare_save(PROJECT / "build" / "probe_housefps.sav")
def idle(e, vbl=90):
    c0 = e.c.cmd("event_counts"); h = 0
    while True:
        e.run_to_pc(0x01FFA3C0, timeout_frames=5)
        c1 = e.c.cmd("event_counts")
        if c1["vblank9"] - c0["vblank9"] >= vbl: break
        e.c.cmd("run_to_event", event="insn9", count=c1["insn9"] + 3, stall=2000)
        h += e.c.cmd("event_counts")["cyc9"] - c1["cyc9"]
    return 100.0 * h / (e.c.cmd("event_counts")["cyc9"] - c0["cyc9"])
with Emu(ROM_VANILLA, str(save), port=19876, tag="housefps") as e:
    e.boot_to_town(); e.wait(300)
    a = e.u32(0x021F7E10); e.wait(300); print("town  game frames/300vbl", e.u32(0x021F7E10) - a, f"idle {idle(e):.1f}%")
    up = RELEASED & ~(1 << KEY_BITS["up"])
    for _ in range(12):
        e.c.cmd("keys", mask=up); e.wait(22); e.c.cmd("keys", mask=up & ~1); e.wait(3)
    e.c.cmd("keys", mask=RELEASED); e.wait(500)
    a = e.u32(0x021F7E10); e.wait(300); print("house game frames/300vbl", e.u32(0x021F7E10) - a, f"idle {idle(e):.1f}%")
    e.shot("house")
