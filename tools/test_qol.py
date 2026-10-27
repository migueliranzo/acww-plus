#!/usr/bin/env python3
"""QOL features (ndsref).
usage: test_qol.py [stage ...]   stages: nook bells bells_full bells_cap museum museum_assess (default: all)

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


NOOK_RAM = 0x021F07AC     # block 0x15DB4, nook_daily_restock's record


def nook_state(rom, tag):
    # +0x51 = 1: nook_restock_date_differs() says yes, so the shop restocks when the town loads (+0x50 = 0x18 kept).
    # Player flags 0x202 -> 0x200: flag 1 (Nook's part-time job not finished) cleared, as for any player past it.
    save = prepare_save(BUILD / f"test_qol_{tag}.sav", pokes={0x15DB4 + 0x50: 0x0118, 0xC + 0x21FC: 0x0200})
    with Emu(rom, str(save), tag=f"qol_{tag}") as e:
        e.boot_to_town()
        e.wait(60)
        return e.read(A(NOOK_RAM) + 0x4C, 0x14)


def nook_run():
    """One-player town (the d25 save, restocked on load): the patched ROM runs the sale-day scheduler, which writes
    the next sale day's date at +0x52; vanilla skips it."""
    v_rec = nook_state(ROM_VANILLA, "nook_v")
    p_rec = nook_state(ROM_PLUS, "nook_p")
    print(f"  [nook] vanilla +0x4C: {v_rec.hex()}")
    print(f"  [nook] plus    +0x4C: {p_rec.hex()}")
    ok = v_rec[6:9] == bytes(3) and p_rec[6:9] != bytes(3)
    print(f"  RESULT nook: {'PASS' if ok else 'FAIL'} (sale day scheduled only with the patch)")
    return ok


MUSEUM_POCKET = [0x12E8, 0x12B0, 0x1549, 0x1549, 0x450C, 0x1392]   # bitterling, butterfly, 2 fossils, amber, fruit


def to_blathers(e):
    """House (acre 9) -> museum door (acre 8, square (23,59)) -> in front of Blathers, talking, choices shown."""
    e.wait(200)
    walk_until(e, "down", 2, 61.5, max_frames=400)
    walk_until(e, "left", 0, 24.2, max_frames=1200)
    walk_until(e, "left", 0, 23.6, max_frames=60, step=1)
    walk_until(e, "up", 2, 58.0, max_frames=300)
    e.wait(400)                                   # museum lobby, entrance at (8, 14.5)
    walk_until(e, "left", 0, 7.6, max_frames=40, step=1)
    walk_until(e, "up", 2, 11.8, max_frames=200, step=2)
    e.press("a", hold=6, after=240)
    for _ in range(5):
        e.press("b", hold=6, after=100)          # speeds the greeting up (on the choices B would pick the last)
    e.press("a", hold=6, after=100)               # choices shown


def museum_run(tag, choice_downs, marks, pick, expect):
    """Opens Blathers' picker (choice index choice_downs), X on the slots in marks, A on pick, then A through the
    talk (yes / "Sure is!" / "Yep!" are the defaults). expect(before, after) checks the pockets."""
    pokes = {0xC + 0x1B22 + 2 * i: (MUSEUM_POCKET[i] if i < len(MUSEUM_POCKET) else 0xFFF1) for i in range(15)}
    save = prepare_save(BUILD / f"test_qol_{tag}.sav", pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"qol_{tag}") as e:
        e.boot_to_town()
        to_blathers(e)
        for _ in range(choice_downs):
            e.press("down", hold=6, after=30)
        e.press("a", hold=6, after=200)           # the topic
        armed = {l.split()[1]: int(l.split()[0], 16) for l in open(BUILD / "heap.map")}["s_armed"]
        for _ in range(20):                       # A through the talk until the picker is requested
            if e.u8(armed):
                break
            e.press("a", hold=6, after=120)
        e.press("a", hold=6, after=400)           # "...what you wish to donate!" -> the picker fades in
        before = pockets(e)
        cur = 0
        for slot in sorted(marks) + [pick]:
            while cur < slot:
                e.press("right", hold=6, after=30)
                cur += 1
            if slot in marks and slot != pick:
                e.press("x", hold=6, after=30)
        e.shot(f"{tag}_marked")
        e.press("a", hold=6, after=200)           # pick
        for _ in range(60):
            e.press("a", hold=6, after=110)
        e.shot(f"{tag}_end")
        after = pockets(e)
        ok = expect(before, after)
        print(f"  [{tag}] pockets {[hex(x) for x in before[:6]]} -> {[hex(x) for x in after[:6]]}")
        print(f"  RESULT {tag}: {'PASS' if ok else 'FAIL'}")
        return ok


def is_fossil(x):
    return 0x450C <= x <= 0x45DB


STAGES = {
    # bitterling and butterfly marked, amber picked: all three donated, the rest untouched
    "museum": lambda: museum_run("museum", 0, {0, 1}, 4, lambda b, a: a[0] == a[1] == a[4] == 0xFFF1
                                 and a[2:4] == b[2:4] and a[5] == b[5]),
    # "Check a fossil!": the first unassessed fossil marked, the second picked: both assessed (and, A being the
    # default answer, then donated too: assessed fossils or empty slots)
    "museum_assess": lambda: museum_run("museum_assess", 1, {2}, 3, lambda b, a: all(
        is_fossil(x) or x == 0xFFF1 for x in a[2:4]) and a[:2] == b[:2] and a[4:6] == b[4:6]),
    "nook": nook_run,
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
