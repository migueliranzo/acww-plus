"""Drop an item from pocket slot 1 south of the house, then walk around it; report frame progress.
usage: drop_item.py ITEM [port]"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
item = int(sys.argv[1], 16); port = int(sys.argv[2]) if len(sys.argv) > 2 else 19891
save = prepare_save(PROJECT / "build" / f"probe_drop_{item:04x}.sav", edits=dict(items=[item]))
def alive(e, label, n=90):
    a = e.u32(0x021F7E10); e.wait(n); b = e.u32(0x021F7E10)
    print(f"  [{label}] game frames {b - a}/{n} vblank, pc={e.regs()['r'][15]:#x}")
    return b - a
with Emu(ROM_PLUS, str(save), port=port, tag=f"drop{item:04x}") as e:
    e.boot_to_town(); e.wait(300)
    walk_until(e, "down", 2, 59.5, max_frames=300)
    e.press("y", hold=6, after=120); e.press("right", hold=6, after=60); e.press("a", hold=6, after=95)
    e.press("down", hold=6, after=40); e.press("a", hold=6, after=200); e.press("y", hold=6, after=120)
    e.shot("01_dropped"); alive(e, "after drop")
    for k, axis, t in (("left", 0, 41.0), ("down", 2, 61.5), ("right", 0, 46.0), ("up", 2, 58.5)):
        walk_until(e, k, axis, t, max_frames=200); alive(e, f"walked {k}", 30)
    e.shot("02_walked")
    rec = 0x021DAA04
    e.press("b", hold=6, after=90)   # pick up attempt
    alive(e, "after B")
    e.shot("03_end")
