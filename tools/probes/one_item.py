"""Place one furniture item next to the house and check the game keeps running. usage: one_item.py ITEM [port]"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
item = int(sys.argv[1], 16); port = int(sys.argv[2]) if len(sys.argv) > 2 else 19890
save = prepare_save(PROJECT / "build" / f"probe_item_{item:04x}.sav", grid={0xC354 + 9 * 512 + (8 * 16 + 12) * 2: item})
with Emu(ROM_PLUS, str(save), port=port, tag=f"item{item:04x}") as e:
    e.boot_to_town()
    for k in range(4):
        a = e.u32(0x021F7E10); e.wait(150); b = e.u32(0x021F7E10)
        pc = e.regs()["r"][15]
        print(f"  t+{(k+1)*150}: game frames {b - a}/150 vblank, ARM9 pc={pc:#x}")
    e.shot("view")
