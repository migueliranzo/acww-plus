#!/usr/bin/env python3
"""Tool swap test (ndsref): R cycles tools from the pockets, L puts away / takes back, no swap in menus or walking."""
import struct
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa

TOOLS = [0x1369, 0x1376, 0x1374]  # shovel, net, fishing rod
NAMES = {0x1369: "shovel", 0x1376: "net", 0x1374: "rod", 0xFFF1: "-"}


def record(e):
    idx = e.u32(e.u32(0x020CC0C8) + 0x68)
    return 0x021DA9F8 + 0xC + 0x228C * idx


def state(e):
    rec = record(e)
    hand = e.u16(rec + 0x220A)
    pk = struct.unpack("<15H", e.read(rec + 0x1B22, 30))
    return hand, pk


def show(e, label):
    hand, pk = state(e)
    tools = [f"{i}:{NAMES.get(v, hex(v))}" for i, v in enumerate(pk) if v in NAMES and v != 0xFFF1]
    a = player_actor(e)
    act = e.u32(a + 0x7EC) if a else -1
    print(f"  [{label}] hand={NAMES.get(hand, hex(hand))} pockets tools={tools} action={act:#x}")
    return hand, pk


def main():
    results = []
    save = prepare_save(PROJECT / "build" / "test_tools.sav", edits=dict(items=TOOLS))
    with Emu(ROM_PLUS, str(save), tag="tools") as e:
        e.boot_to_town()
        e.wait(300)
        h0, _ = show(e, "start")
        hands = []
        for i in range(4):
            e.press("r", hold=6, after=90)
            h, _ = show(e, f"R #{i+1}")
            hands.append(h)
        e.shot("01_after_r")
        results.append(("R cycles through the 3 tools and wraps",
                        set(hands[:3]) == set(TOOLS) and hands[3] == hands[0]))
        # quick double tap: the second tap lands during the equip animation and must be buffered
        before = state(e)[0]
        e.press("r", hold=6, after=14)
        e.press("r", hold=6, after=120)
        h, _ = show(e, "R R (double tap)")
        results.append(("a tap during the animation is buffered", h not in (before, 0xFFF1) and h in TOOLS))
        e.press("l", hold=6, after=90)
        h5, pk5 = show(e, "L (put away)")
        e.shot("02_after_l")
        results.append(("L puts the tool away", h5 == 0xFFF1 and h in pk5))
        e.press("l", hold=6, after=90)
        h6, _ = show(e, "L (take back)")
        results.append(("L takes it back out", h6 == h))
        # Pockets open: R must not swap
        e.press("y", hold=6, after=120)
        e.press("r", hold=6, after=60)
        e.shot("03_menu_r")
        e.press("b", hold=6, after=120)
        h7, _ = show(e, "R inside the pockets menu, menu closed")
        results.append(("no swap while the pockets menu is open", h7 == h6))
        # Walking with R held (running) must not swap
        e.press(["right", "r"], hold=40, after=60)
        h8, _ = show(e, "walk right with R held")
        results.append(("no swap while running with R", h8 == h7))
        e.press("r", hold=6, after=90)
        h9, _ = show(e, "R after the menu and the walk")
        results.append(("still works after menu + walk", h9 != h8 and h9 in TOOLS))
        e.shot("04_end")
    print()
    for name, ok in results:
        print(f"  RESULT {name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
