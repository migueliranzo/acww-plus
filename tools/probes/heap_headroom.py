"""Root-heap headroom: walks the NitroSystem expanded heap inside the game's root heap (handle at *0x021F7ECC,
'EXPH' head at +0x30) and reports heap size, total free, largest free block, and the free block count.
Measures in town (settled), with the 24-piece furniture stress yard, inside the house and back in town, on the
vanilla ROM and on AC:WW+.
usage: py -3.12 tools/probes/heap_headroom.py [plus|vanilla|both]"""
import struct
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa

GRID_SAVE = 0xC354


def heap_stats(e):
    h = e.u32(0x021F7ECC)
    x = h + 0x30
    sig, = struct.unpack("<I", e.read(x, 4))
    if sig != 0x45585048:   # 'EXPH'
        return None
    start, end = struct.unpack("<2I", e.read(x + 0x18, 8))
    blk = e.u32(x + 0x24)
    total = largest = n = 0
    while blk and n < 4096:
        sz = e.u32(blk + 4)
        total += sz
        largest = max(largest, sz)
        n += 1
        blk = e.u32(blk + 12)
    return dict(handle=h, size=end - start, free=total, largest=largest, blocks=n)


def show(label, st):
    print(f"  [{label}] heap {st['size'] / 1024:.0f} KB at {st['handle']:#x}, free {st['free'] / 1024:.1f} KB, "
          f"largest {st['largest'] / 1024:.1f} KB in {st['blocks']} free blocks")
    return st


def run(rom, tag):
    yard = {}
    i = 0
    for lz in (8, 10, 12, 13):          # 24 different furniture pieces around the house (acre 9)
        for lx in (2, 3, 4, 5, 6, 13, 14):
            if i < 24:
                yard[GRID_SAVE + 9 * 512 + (lz * 16 + lx) * 2] = 0x3000 + 4 * (i * 7 + 2)
                i += 1
    save = prepare_save(PROJECT / "build" / f"probe_heap_{tag}.sav", edits=dict(bells=50000), grid=yard)
    out = {}
    with Emu(rom, str(save), tag=f"heap_{tag}") as e:
        e.boot_to_town()
        e.wait(400)
        out["town"] = show(f"{tag} town, 24 pieces", heap_stats(e))
        walk_until(e, "down", 2, 61.0, max_frames=300)
        e.wait(200)
        out["town2"] = show(f"{tag} town, walked south", heap_stats(e))
        e.press("y", hold=6, after=150)
        out["pockets"] = show(f"{tag} town, pockets open", heap_stats(e))
        e.press("y", hold=6, after=150)
        e.press("start", hold=6, after=150)
        out["start"] = show(f"{tag} town, start menu open", heap_stats(e))
        e.shot("start_menu")
        e.press("b", hold=6, after=150)
        e.press("start", hold=6, after=150)
        walk_until(e, "up", 2, 55.2, max_frames=300)
        up = RELEASED & ~(1 << KEY_BITS["up"])
        for _ in range(12):
            e.c.cmd("keys", mask=up)
            e.wait(22)
            e.c.cmd("keys", mask=up & ~(1 << KEY_BITS["a"]))
            e.wait(3)
        e.c.cmd("keys", mask=RELEASED)
        e.wait(400)
        out["house"] = show(f"{tag} in the house", heap_stats(e))
        e.press("down", hold=120, after=500)
        e.wait(300)
        out["back"] = show(f"{tag} back in town", heap_stats(e))
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("vanilla", "both"):
        run(ROM_VANILLA, "vanilla")
    if which in ("plus", "both"):
        run(ROM_PLUS, "plus")
