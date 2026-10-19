import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
save = prepare_save(PROJECT / "build" / "probe_fc.sav")
with Emu(ROM_PLUS, str(save), port=19899, tag="fc") as e:
    e.boot_to_town(); e.wait(60)
    for i in range(6):
        print(e.v(), hex(e.u32(0x021F7E10)), hex(e.u16(0x021F7E80)), hex(e.u16(0x021F7E82)))
        e.wait(1)
    e.c.cmd("keys", mask=RELEASED & ~(1 << KEY_BITS["r"]))
    for i in range(6):
        e.wait(1); print("R", e.v(), hex(e.u32(0x021F7E10)), hex(e.u16(0x021F7E80)), hex(e.u16(0x021F7E82)))
    e.c.cmd("keys", mask=RELEASED)
