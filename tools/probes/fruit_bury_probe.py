#!/usr/bin/env python3
"""Fruit stacks: dig a hole west of the door and bury 3 apples in it; screenshot the item menu and report pockets and ground.
usage: fruit_bury_probe.py"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from harness import *  # noqa

pokes = {0xC + 0x1B22 + 2 * i: 0xFFF1 for i in range(15)}
pokes[0xC + 0x1B22] = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x156F   # 3 apples
pokes[0xC + 0x1B22 + 2] = 0x1369    # shovel (equipped with R)
save = prepare_save(BUILD / "probe_fruit_bury.sav", pokes=pokes)
with Emu(ROM_PLUS, str(save), tag="fruit_bury") as e:
    e.boot_to_town()
    e.wait(200)
    grid = SAVE_RAM_BASE + 0xC354 + 9 * 512
    before = e.read(grid, 512)
    walk_until(e, "left", 0, float(sys.argv[1]) if len(sys.argv) > 1 else 38.5, max_frames=400)
    walk_until(e, "down", 2, 57.5, max_frames=200)
    e.press("r", hold=6, after=90)
    e.shot("spot")
    rec = SAVE_RAM_BASE + 0xC
    print("  hand", hex(e.u16(rec + 0x220A)), "unit", player_unit(e))
    e.press("a", hold=6)                  # dig
    seen = []
    for _ in range(75):
        e.wait(4)
        a = e.u32(player_actor(e) + 0x7EC)
        if not seen or seen[-1] != a:
            seen.append(a)
    print("  actions:", [hex(a) for a in seen])
    e.shot("dug")
    after = e.read(grid, 512)
    print("  player", player_pos(e) if "player_pos" in globals() else "?")
    print("  acre 9 changes:", [(i % 16, i // 16, hex(struct.unpack_from("<H", before, 2 * i)[0]), hex(struct.unpack_from("<H", after, 2 * i)[0])) for i in range(256) if before[2 * i:2 * i + 2] != after[2 * i:2 * i + 2]])
    e.press("y", hold=6, after=120)
    e.press("a", hold=6, after=60)
    e.shot("menu")
    e.press("down", hold=6, after=40)
    e.press("down", hold=6, after=40)     # Grab / Drop on Ground / Bury / Never Mind
    e.shot("menu_down")
    e.press("a", hold=6, after=400)
    e.shot("buried")
    e.press("y", hold=6, after=200)
    e.shot("closed")
    rec = SAVE_RAM_BASE + 0xC
    end = e.read(grid, 512)
    print("  acre 9 changes after the drop:", [(i % 16, i // 16, hex(struct.unpack_from("<H", after, 2 * i)[0]), hex(struct.unpack_from("<H", end, 2 * i)[0])) for i in range(256) if after[2 * i:2 * i + 2] != end[2 * i:2 * i + 2]])
    print("  slots:", [hex(x) for x in struct.unpack("<15H", e.read(rec + 0x1B22, 30))])
