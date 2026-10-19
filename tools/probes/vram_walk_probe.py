import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
save = prepare_save(PROJECT / "build" / "probe_walk.sav")
def snap(e):
    vals = [e.u32(0x021F2CD4) - e.u32(0x021F2CB0)] + [e.u32(0x021F2CB4+4*i) - e.u32(0x021F2CC4+4*i) for i in range(4)]
    return tuple(vals)
with Emu(ROM_VANILLA, str(save), port=19896, tag="vramwalk") as e:
    e.boot_to_town(); e.wait(210)
    base = snap(e); print("base", [hex(x) for x in base])
    route = ["down"]*4 + ["left"]*6 + ["down"]*6 + ["right"]*10 + ["up"]*6 + ["right"]*8 + ["down"]*8 + ["left"]*12
    mins = list(base)
    for i, k in enumerate(route):
        e.press(k, hold=40)
        s = snap(e)
        mins = [min(a, b) for a, b in zip(mins, s)]
        if s != base:
            print(i, k, "changed", [hex(x) for x in s])
    print("mins", [hex(x) for x in mins])
    e.shot("end")
