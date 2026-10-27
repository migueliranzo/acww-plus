#!/usr/bin/env python3
"""QOL features (ndsref).
usage: test_qol.py [stage ...]   stages: see STAGES (default: all)

bells*: a 1,000-Bell bag on the square south of the door (acre 9 (11,8)); the player steps out of the house facing
it and presses B. It stacks onto a pocket bag when the total is a bag (bells, bells_full), else takes a free slot
(bells_new, bells_nostack). The wallet never changes. fruit*: the same with fruit, which stacks up to 9;
fruit_eat / fruit_bury / fruit_drop use the pockets screen (see pocket_menu_run).
museum*: walks to Blathers and shows him several items at once (see museum_run)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from harness import *  # noqa

GRID_SAVE = 0xC354
BAG_1000 = 0x149B
FILLER = 0x1392        # any plain pocket item to fill the pockets
APPLE, ORANGE = 0x1518, 0x1519


def apples(n):
    """The fruit-stack item for n apples (src/heap/fruit_stack.c)."""
    return APPLE if n == 1 else 0x156E + n - 2


def tile_off(acre, lx, lz):
    return GRID_SAVE + acre * 512 + (lz * 16 + lx) * 2


def player_rec(e):
    return SAVE_RAM_BASE + 0xC + 0x228C * e.u32(e.u32(A(0x020CC0C8)) + 0x68)


def pockets(e):
    return list(struct.unpack("<15H", e.read(player_rec(e) + 0x1B22, 30)))


def wallet(e):
    return e.u32(player_rec(e) + 0x1B40)


def bells_run(tag, pocket_items, expect_pockets, ground=BAG_1000):
    """B on an item (a 1,000-Bell bag) south of the door with the given pockets; the wallet (5,000) must not change."""
    pokes = {0xC + 0x1B22 + 2 * i: (pocket_items[i] if i < len(pocket_items) else 0xFFF1) for i in range(15)}
    pokes[tile_off(9, 11, 8)] = ground
    save = prepare_save(BUILD / f"test_qol_{tag}.sav", edits=dict(bells=5000), pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"qol_{tag}") as e:
        e.boot_to_town()
        e.wait(200)
        walk_until(e, "down", 2, 55.8, max_frames=60)    # facing the bag square
        w0 = wallet(e)
        e.press("b", hold=6, after=200)
        e.shot(f"qol_{tag}")
        w1, p1 = wallet(e), pockets(e)
        tile = e.u16(SAVE_RAM_BASE + tile_off(9, 11, 8))
        want = expect_pockets + [0xFFF1] * (15 - len(expect_pockets))
        ok = p1 == want and w1 == w0 and tile == 0xFFF1
        print(f"  [{tag}] pockets {[hex(x) for x in p1[:8]]} (expect {[hex(x) for x in want[:8]]}), "
              f"wallet {w0} -> {w1}, ground={tile:#06x}")
        print(f"  RESULT {tag}: {'PASS' if ok else 'FAIL'}")
        return ok


def pocket_menu_run(tag, first, dig, menu_downs, expect_slot0, expect_ground=None):
    """Pockets screen (Y) on slot 0 = `first`, then the item menu (A) and its entry `menu_downs` down:
    Grab (0, then the player's portrait: eat), Drop on Ground (1), Bury (2, only facing a hole). With `dig`, the
    player first digs a hole west of the house with the shovel (slot 1, equipped with R). The pockets are read back
    after the screen closes; `expect_ground` is the square the item went to (the hole, or the player's square)."""
    pokes = {0xC + 0x1B22 + 2 * i: 0xFFF1 for i in range(15)}
    pokes[0xC + 0x1B22] = first
    if dig:
        pokes[0xC + 0x1B22 + 2] = 0x1369      # shovel
    save = prepare_save(BUILD / f"test_qol_{tag}.sav", pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"qol_{tag}") as e:
        e.boot_to_town()
        e.wait(200)
        walk_until(e, "left", 0, 35.5, max_frames=400)
        walk_until(e, "down", 2, 57.5, max_frames=200)       # acre 9 (2, 10), facing (2, 11)
        if dig:
            e.press("r", hold=6, after=90)
            e.press("a", hold=6, after=300)
        e.press("y", hold=6, after=120)
        e.press("a", hold=6, after=60)
        for _ in range(menu_downs):
            e.press("down", hold=6, after=40)
        e.press("a", hold=6, after=60)
        if menu_downs == 0:                                   # grabbed: up to the portrait, A = eat
            for _ in range(3):
                e.press("up", hold=6, after=40)
            e.press("a", hold=6, after=90)
        e.wait(400)
        e.shot(f"qol_{tag}")
        e.press("b", hold=6, after=60)
        e.press("y", hold=6, after=200)
        p = pockets(e)
        ground = {sq: e.u16(SAVE_RAM_BASE + tile_off(9, *sq)) for sq in ((2, 10), (2, 11))}
        ok = p[0] == expect_slot0 and all(x == 0xFFF1 for x in p[1 + dig:])
        if expect_ground:
            ok = ok and ground[expect_ground[0]] == expect_ground[1]
        print(f"  [{tag}] slot 0 {p[0]:#06x} (expect {expect_slot0:#06x}), ground "
              f"{ {k: hex(v) for k, v in ground.items()} } (expect {expect_ground})")
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
    # a 1,000 bag already in slot 1: it becomes a 2,000 bag
    "bells": lambda: bells_run("bells", [FILLER, BAG_1000, FILLER], [FILLER, BAG_1000 + 1, FILLER]),
    # same with full pockets (no "pockets are full" talk)
    "bells_full": lambda: bells_run("bells_full", [FILLER, BAG_1000] + [FILLER] * 13,
                                    [FILLER, BAG_1000 + 1] + [FILLER] * 13),
    # no bag in the pockets: the bag takes the first free slot (vanilla)
    "bells_new": lambda: bells_run("bells_new", [FILLER] * 2, [FILLER, FILLER, BAG_1000]),
    # a 900 bag: 1,900 is no bag, so the new one gets its own slot
    "bells_nostack": lambda: bells_run("bells_nostack", [0x149A], [0x149A, BAG_1000]),
    # an apple picked up with an apple in the pockets: "2 apples"
    "fruit": lambda: bells_run("fruit", [FILLER, APPLE], [FILLER, apples(2)], ground=APPLE),
    # 8 + 1 = 9 apples, with full pockets
    "fruit_full": lambda: bells_run("fruit_full", [apples(8)] + [FILLER] * 14, [apples(9)] + [FILLER] * 14,
                                    ground=APPLE),
    # 9 apples is the most: the next apple gets its own slot
    "fruit_max": lambda: bells_run("fruit_max", [apples(9)], [apples(9), APPLE], ground=APPLE),
    # an orange does not join the apples
    "fruit_kind": lambda: bells_run("fruit_kind", [APPLE], [APPLE, ORANGE], ground=ORANGE),
    # a dropped stack of 3 picked up again joins 4 apples: 7
    "fruit_stack": lambda: bells_run("fruit_stack", [apples(4)], [apples(7)], ground=apples(3)),
    # eating from 3 apples: 2 stay in the slot
    "fruit_eat": lambda: pocket_menu_run("fruit_eat", apples(3), False, 0, apples(2)),
    # burying 3 apples in a hole plants one apple sapling (0x37, as vanilla for one apple); 2 stay
    "fruit_bury": lambda: pocket_menu_run("fruit_bury", apples(3), True, 2, apples(2), ((2, 11), 0x37)),
    # dropping a stack drops all of it
    "fruit_drop": lambda: pocket_menu_run("fruit_drop", apples(3), False, 1, 0xFFF1, ((2, 10), apples(3))),
}


def main():
    res = [(s, STAGES[s]()) for s in (sys.argv[1:] or list(STAGES))]
    for s, ok in res:
        print(f"  {s}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
