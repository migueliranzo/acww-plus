#!/usr/bin/env python3
"""QOL features (ndsref).
usage: test_qol.py [stage ...]   stages: bells bells_full bells_cap (default: all)

bells*: a Bell bag on the square south of the door (acre 9 (11,8)); the player steps out of the house facing it
and presses B. A bag that fits in the wallet goes there, with free pockets (bells) or full ones (bells_full); with
the wallet near the 99,999 cap (bells_cap) the bag is pocketed as in vanilla."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from harness import *  # noqa

GRID_SAVE = 0xC354
BAG_1000 = 0x149B
FILLER = 0x1392        # any plain pocket item (a fruit) to fill the pockets


def tile_off(acre, lx, lz):
    return GRID_SAVE + acre * 512 + (lz * 16 + lx) * 2


def player_rec(e):
    return SAVE_RAM_BASE + 0xC + 0x228C * e.u32(e.u32(A(0x020CC0C8)) + 0x68)


def pockets(e):
    return list(struct.unpack("<15H", e.read(player_rec(e) + 0x1B22, 30)))


def wallet(e):
    return e.u32(player_rec(e) + 0x1B40)


def bells_run(tag, bells, pocket_items, expect_wallet, expect_in_pocket):
    pokes = {0xC + 0x1B22 + 2 * i: (pocket_items[i] if i < len(pocket_items) else 0xFFF1) for i in range(15)}
    pokes[tile_off(9, 11, 8)] = BAG_1000
    save = prepare_save(BUILD / f"test_qol_{tag}.sav", edits=dict(bells=bells), pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"qol_{tag}") as e:
        e.boot_to_town()
        e.wait(200)
        walk_until(e, "down", 2, 55.8, max_frames=60)    # facing the bag square
        w0, p0 = wallet(e), pockets(e)
        e.press("b", hold=6, after=200)
        e.shot(f"qol_{tag}")
        w1, p1 = wallet(e), pockets(e)
        tile = e.u16(SAVE_RAM_BASE + tile_off(9, 11, 8))
        bag_pocketed = p1.count(BAG_1000) > p0.count(BAG_1000)
        ok = w1 == expect_wallet and bag_pocketed == expect_in_pocket and tile == 0xFFF1
        print(f"  [{tag}] wallet {w0} -> {w1} (expect {expect_wallet}), bag pocketed={bag_pocketed} "
              f"(expect {expect_in_pocket}), ground={tile:#06x}")
        print(f"  RESULT {tag}: {'PASS' if ok else 'FAIL'}")
        return ok


STAGES = {
    "bells": lambda: bells_run("bells", 5000, [FILLER] * 3, 6000, False),
    "bells_full": lambda: bells_run("bells_full", 5000, [FILLER] * 15, 6000, False),
    "bells_cap": lambda: bells_run("bells_cap", 99500, [FILLER] * 3, 99500, True),
}


def main():
    res = [(s, STAGES[s]()) for s in (sys.argv[1:] or list(STAGES))]
    for s, ok in res:
        print(f"  {s}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
