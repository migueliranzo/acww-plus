#!/usr/bin/env python3
"""Walks from the house (acre 9) to the museum (acre 8, door (23,59)), enters, talks to Blathers. Screenshots each step.
usage: museum_probe.py [rom]"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from harness import *  # noqa

POCKET = [0x12E8, 0x12B0, 0x1549, 0x1549, 0x450C, 0x1392]


def where(e, label):
    x, _, z, _ = player_pos(e)
    print(f"  v{e.v()} {label}: x={x / 8192:.2f} z={z / 8192:.2f}")
    return x / 8192, z / 8192


def main():
    rom = sys.argv[1] if len(sys.argv) > 1 else ROM_PLUS
    pokes = {0xC + 0x1B22 + 2 * i: (POCKET[i] if i < len(POCKET) else 0xFFF1) for i in range(15)}
    save = prepare_save(BUILD / "probe_museum.sav", pokes=pokes)
    with Emu(rom, str(save), tag="museum") as e:
        e.boot_to_town()
        e.wait(200)
        walk_until(e, "down", 2, 61.5, max_frames=400)
        where(e, "row 61")
        walk_until(e, "left", 0, 24.2, max_frames=1200)
        walk_until(e, "left", 0, 23.6, max_frames=60, step=1)
        where(e, "below the museum")
        e.shot("m1_below_museum")
        walk_until(e, "up", 2, 58.0, max_frames=300)
        where(e, "at the door")
        e.wait(400)
        e.shot("m2_entered")
        print("  actor:", hex(player_actor(e)))
        try:
            where(e, "inside")
        except Exception as ex:
            print("  pos failed", ex)
        walk_until(e, "left", 0, 7.6, max_frames=40, step=1)
        where(e, "shifted")
        walk_until(e, "up", 2, 11.8, max_frames=200, step=2)
        where(e, "walked up")
        e.shot("m3_walked_up")
        e.press("a", hold=6, after=240)
        e.shot("m4_talk")
        for i in range(5):
            e.press("b", hold=6, after=100)      # B speeds the greeting up (on the choice it would pick the last one)
        e.shot("m5_choice")
        e.press("a", hold=6, after=100)          # shows the choices
        e.press("a", hold=6, after=100)          # Donation!
        e.press("a", hold=6, after=200)          # "...what you wish to donate!" -> picker
        e.shot("m6_picker")
        e.press("a", hold=6, after=300)
        e.shot("m6_picker2")
        rec = player_rec_addr(e)
        print("  pockets before:", [hex(x) for x in struct.unpack("<15H", e.read(rec + 0x1B22, 30))])
        e.press("x", hold=6, after=30)
        e.press("right", hold=6, after=30)
        e.press("x", hold=6, after=30)
        e.shot("m7_marked")
        hm = {l.split()[1]: int(l.split()[0], 16) for l in open(BUILD / "heap.map")}
        print(f"  armed={e.u8(hm['s_armed'])} marks={e.u16(hm['s_marks']):#06x}")
        for _ in range(3):
            e.press("right", hold=6, after=30)
        e.press("a", hold=6, after=200)
        for i in range(40):
            e.shot(f"m8_{i:02d}")
            e.press("a", hold=6, after=110)
        print("  pockets after:", [hex(x) for x in struct.unpack("<15H", e.read(rec + 0x1B22, 30))])


def player_rec_addr(e):
    return SAVE_RAM_BASE + 0xC + 0x228C * e.u32(e.u32(A(0x020CC0C8)) + 0x68)


main()
