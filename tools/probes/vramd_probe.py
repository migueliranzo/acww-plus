"""How much of VRAM D (ARM7 WRAM in town) is used / changing. usage: vramd_probe.py"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
save = prepare_save(PROJECT / "build" / "probe_vramd.sav")
with Emu(ROM_VANILLA, str(save), port=19885, tag="vramd") as e:
    e.boot_to_town(); e.wait(300)
    a = e.read_region("vramD") if hasattr(e, "read_region") else e.c.read_region("vramD")
    e.wait(600)
    b = e.c.read_region("vramD")
    print("vramD size", hex(len(a)))
    blk = 0x1000
    used = [i for i in range(0, len(a), blk) if any(a[i:i+blk])]
    changed = [i for i in range(0, len(a), blk) if a[i:i+blk] != b[i:i+blk]]
    print("non-zero 4KB blocks:", len(used), [hex(i) for i in used][:40])
    print("changed 4KB blocks over 600 vblanks:", len(changed), [hex(i) for i in changed][:40])
    # what's at the start: code-like?
    print("first bytes", a[:64].hex())
    last = max(i for i in range(len(a)) if a[i]) if any(a) else -1
    print("highest non-zero byte offset", hex(last))
