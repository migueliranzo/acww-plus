#!/usr/bin/env python3
"""Tree shake with a rod / net equipped (ndsref). The tree at acre 9 (12,14) is south of the player's house."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[0]))
from harness import *  # noqa

ROD, NET = 0x1374, 0x1376


def action(e):
    return e.u32(player_actor(e) + 0x7EC)


def watch_actions(e, frames):
    seen = []
    for _ in range(frames // 4):
        e.wait(4)
        a = action(e)
        if not seen or seen[-1] != a:
            seen.append(a)
    return seen


def run(tool, rom, tag):
    tree_off = 0xC354 + 9 * 512 + (9 * 16 + 11) * 2      # acre 9 (11,9): two squares south of the door
    save = prepare_save(PROJECT / "build" / f"test_shake_{tag}.sav", edits=dict(items=[tool]), grid={tree_off: 0x002A})
    with Emu(rom, str(save), tag=f"shake_{tag}") as e:
        e.boot_to_town()
        e.wait(300)
        # go to x=44.5 (column 12), then down until blocked by the tree at row 14 (z 62..63)
        x, z = walk_until(e, "down", 2, 58.0, max_frames=300)   # blocked by the tree at z 57..58
        print(f"  [{tag}] in front of the tree: x={x:.2f} z={z:.2f}")
        # equip the tool from the pockets (vanilla ROM: the pocket screen; plus ROM: R)
        if rom == ROM_PLUS:
            e.press("r", hold=6, after=90)
        else:
            e.press("y", hold=6, after=120)
            e.press("right", hold=4, after=40)
            e.press("a", hold=4, after=80)
            e.press("a", hold=4, after=80)   # first menu entry: equip / hold
            e.press("b", hold=6, after=120)
        rec = 0x021DA9F8 + 0xC + 0x228C * e.u32(e.u32(0x020CC0C8) + 0x68)
        print(f"  [{tag}] hand={e.u16(rec + 0x220A):#06x} action={action(e):#x}")
        e.press("a", hold=6)
        seen = watch_actions(e, 120)
        e.shot("after_a")
        print(f"  [{tag}] actions after A: {[hex(a) for a in seen]}  hand={e.u16(rec + 0x220A):#06x}")
        return seen


def main():
    which = sys.argv[1:] or ["rod", "net"]
    res = []
    for w in which:
        seen = run(ROD if w == "rod" else NET, ROM_PLUS, w)
        res.append((w, 0x68 in seen or 0x69 in seen))
    for w, ok in res:
        print(f"  RESULT {w}: A in front of a tree shakes it: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
