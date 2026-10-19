import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
which = sys.argv[1]
rom = ROM_VANILLA if which == "vanilla" else ROM_PLUS
save = prepare_save(PROJECT / "build" / f"probe_{which}.sav")
with Emu(rom, str(save), port=19896 if which == "vanilla" else 19897, tag=f"vram_{which}") as e:
    e.boot_to_town(); e.wait(210)
    pc, pe = e.u32(0x021F2CB0), e.u32(0x021F2CD4)
    print(which, "pltt free", hex(pe - pc))
    for i in range(4):
        hi, lo = e.u32(0x021F2CB4 + 4*i), e.u32(0x021F2CC4 + 4*i)
        print(which, f"tex region {i}: lo={lo:#x} hi={hi:#x} free={hi-lo:#x}")
    if which != "vanilla":
        sc = e.u32(payload_symbols()["s_cache"]); print("s_cache", hex(sc))
    e.shot("town")
