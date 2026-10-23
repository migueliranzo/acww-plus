#!/usr/bin/env python3
"""
Outdoor furniture test (ndsref, headless).
Yard around the player's house (acre 9) gets 1x1, 2-square (two facings) and 2x2 pieces, with more distinct
models than the old fixed 5-slot cache could hold. Pockets get a 2x2 bed, a 2-square couch and a chair.
Checks: 3D draw, cache state, F031 markers on secondary squares, pocket drop, teardown on entering the house.
usage: test_furniture.py [stage ...]   stages: collide drop house marker pickup, or ghost alone (default: all)
"""
import struct
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[0]))
from harness import *  # noqa

GRID_SAVE = 0xC354
GRID_RAM = SAVE_RAM_BASE + GRID_SAVE
ALWAYS = open(PROJECT / "build" / "extracted" / "files" / "ftr_info" / "ENG" / "always.bin", "rb").read()


def footprint(item):
    return ALWAYS[((item - 0x3000) >> 2) * 8 + 5]


def tile_off(acre, lx, lz):
    return GRID_SAVE + acre * 512 + (lz * 16 + lx) * 2


YARD = [  # (lx, lz, item) in acre 9; the house is at (11,5), its door square (11,7)
    (7, 9, 0x3000),   # exotic bed, 2x2 -> (7..8, 9..10)
    (13, 9, 0x300C),  # exotic bench, 2-square, facing 0
    (13, 11, 0x3015), # exotic table, 2-square, facing 1
    (9, 8, 0x301C),   # exotic lamp
    (12, 7, 0x3013),  # exotic chair, facing 3
    (13, 7, 0x303B),  # ranch armchair
    (14, 7, 0x3074),  # classic clock
    (5, 8, 0x3004),   # 1x1 models 0x1, 0x2, 0x6 (more distinct models than 5)
    (4, 8, 0x3008),
    (3, 8, 0x3018),
]
POCKETS = [0x3050, 0x3034, 0x305C]


def dump_grid(e, acre, lz0, lz1):
    for lz in range(lz0, lz1):
        row = e.read(GRID_RAM + acre * 512 + lz * 32, 32)
        print(f"   z{lz:2d} " + " ".join(f"{struct.unpack_from('<H', row, x*2)[0]:04x}" for x in range(16)))


def cache_state(e, label):
    syms = payload_symbols()
    sc = e.u32(syms["s_cache"])
    print(f"  [cache {label}] s_cache=0x{sc:08X}")
    if 0x02000000 <= sc < 0x02400000:
        hdr = struct.unpack("<16I2i", e.read(sc, 72))[:8] + struct.unpack("<16I2i", e.read(sc, 72))[10:]
        print(f"     magic={hdr[0]:#x} tick={hdr[1]} fseq={hdr[3]} ctx={hdr[4]:#x} heap_free={hdr[5]:#x} "
              f"fails={hdr[6]} retry={hdr[7]} arenas={hdr[8]:#x}/{hdr[10]:#x} {hdr[9]:#x}/{hdr[11]:#x} "
              f"pltt={hdr[12]:#x} claimed={hdr[13]}")
        slot_sz = 232   # sizeof(OutdoorFtrSlot)
        print(f"     player grid=({hdr[14]},{hdr[15]})")
        for i in range(12):
            b = e.read(sc + 72 + i * slot_sz, 24)
            mid, ar, dist, off, sz, tick, fseq, arc, mdl = struct.unpack("<HBBHHIIII", b)
            if mid != 0xFFFF:
                print(f"     slot{i}: model={mid:#06x} arena={ar} dist={dist} off={off:#x} size={sz:#x} tick={tick} arc={arc:#x}")
    vr = [e.u32(0x021F2CB4 + 4*i) - e.u32(0x021F2CC4 + 4*i) for i in range(4)]
    print(f"     vram tex free={[hex(x) for x in vr]} pltt free={e.u32(0x021F2CD4) - e.u32(0x021F2CB0):#x}")
    return sc


def where(e, label):
    x, y, z, ang = player_pos(e)
    print(f"  [{label}] player x={x/8192:.2f} z={z/8192:.2f} angle={ang:#06x} dbg={dbg(e)}")
    return x / 8192, z / 8192


def grid_at(e, acre, lx, lz):
    return e.u16(GRID_RAM + acre * 512 + (lz * 16 + lx) * 2)


# Global unit coordinates: acre 9 local (lx, lz) = global (32 + lx, 48 + lz); a unit's centre is +0.5.
def G(lx, lz):
    return 32 + lx + 0.5, 48 + lz + 0.5


def stage_collide(e):
    """Walk to row 10 (left of the table), then right into the table's secondary square (13,10)."""
    where(e, "start")
    x, z = walk_until(e, "down", 2, G(0, 10)[1]); print(f"  at x={x:.2f} z={z:.2f}")
    x, z = walk_until(e, "right", 0, 47.0, max_frames=300)
    print(f"  after walking right on row 10: x={x:.2f} z={z:.2f}")
    e.shot("10_collide_secondary")
    ok = 44.0 < x < 45.0   # square (13,10) spans x 45..46; stop expected before ~44.6
    print(f"  RESULT secondary-square collision: {'PASS' if ok else 'FAIL'} (x={x:.2f}, expected 44.0..45.0)")
    print(f"  orphan marker at (11,9) now {grid_at(e, 9, 11, 9):#06x} (expect fff1)")
    dump_grid(e, 9, 6, 13)


def stage_drop(e):
    """Drop the classic bed (2x2, pocket slot 1) on open ground south of the house (acre 9 row 13)."""
    x, z = walk_until(e, "down", 2, G(0, 13)[1]); print(f"  drop spot x={x:.2f} z={z:.2f}")
    e.press("y", after=120)
    e.shot("20_pockets")
    e.press("right", after=60)
    e.press("a", after=95)
    e.press("down", after=40)
    e.shot("21_drop_menu")
    e.press("a", after=200)
    e.press("y", after=120)
    e.shot("22_after_drop")
    walk_until(e, "left", 0, x - 1.0, max_frames=80)   # move so collision queries run around the bed
    e.shot("23_after_nudge")
    walk_until(e, "right", 0, x + 2.5, max_frames=150)
    walk_until(e, "down", 2, z + 1.5, max_frames=100)
    e.shot("24_view_bed")
    print("  grid rows 11..16 after the drop:")
    dump_grid(e, 9, 11, 16)
    cache_state(e, "after drop")


def stage_house(e):
    """Enter the house from the doorstep, check the cache is gone, come back out."""
    cache_state(e, "before house")
    up = RELEASED & ~(1 << KEY_BITS["up"])
    for _ in range(12):   # Up held onto the door pin, A every 25 vblanks (acww_enter_house.json)
        e.c.cmd("keys", mask=up)
        e.wait(22)
        e.c.cmd("keys", mask=up & ~(1 << KEY_BITS["a"]))
        e.wait(3)
    e.c.cmd("keys", mask=RELEASED)
    e.wait(400)
    e.shot("30_in_house")
    sc = cache_state(e, "in house")
    print(f"  RESULT teardown: {'PASS' if sc == 0 else 'FAIL'} (s_cache={sc:#x})")
    e.press("down", hold=120, after=500)
    e.shot("31_back_outside")
    e.wait(210)
    e.shot("32_back_outside_settled")
    cache_state(e, "back outside")


def stage_pickup(e):
    """Facing the table's marker square (13,10) from the left: B must not pick up the marker.
    Then face the bench anchor (13,9) from below-left... and pick it up: markers must be cleaned up."""
    stage_collide(e)
    e.press("b", after=60)
    e.shot("40_b_on_marker")
    print(f"  after B on marker: (13,10)={grid_at(e, 9, 13, 10):#06x} table (13,11)={grid_at(e, 9, 13, 11):#06x}")
    e.press("b", after=60)
    e.press("a", after=60)
    e.shot("41_a_on_marker")
    print(f"  after A on marker: (13,10)={grid_at(e, 9, 13, 10):#06x}")
    # Step down to row 11 and face right: the table anchor (13,11) is in front
    walk_until(e, "down", 2, G(0, 11)[1], max_frames=60)
    walk_until(e, "right", 0, 47.0, max_frames=60)
    where(e, "facing table anchor")
    e.press("b", after=90)
    e.shot("42_b_on_anchor")
    print(f"  after B on anchor: (13,11)={grid_at(e, 9, 13, 11):#06x} (13,10)={grid_at(e, 9, 13, 10):#06x}")
    walk_until(e, "up", 2, G(0, 9)[1], max_frames=90)
    print(f"  after walking past: (13,10)={grid_at(e, 9, 13, 10):#06x} (expect fff1 if the table was taken)")
    dump_grid(e, 9, 8, 13)


def stage_marker_only(e):
    """Stand right of the 2x2 bed (7..8, 9..10) on row 10, facing its marker square (8,10); press B."""
    walk_until(e, "down", 2, G(0, 10)[1] - 1.0)
    walk_until(e, "left", 0, 40.0, max_frames=400)
    x, z = where(e, "left of path, facing bed marker (8,10)")
    e.press("b", after=90)
    e.shot("50_b_marker_only")
    print(f"  bed squares: (7,9)={grid_at(e, 9, 7, 9):#06x} (8,9)={grid_at(e, 9, 8, 9):#06x} "
          f"(7,10)={grid_at(e, 9, 7, 10):#06x} (8,10)={grid_at(e, 9, 8, 10):#06x}")
    ok = 41.0 <= x < 42.0 and grid_at(e, 9, 8, 10) == 0xF031 and grid_at(e, 9, 7, 9) == 0x3000
    print(f"  RESULT marker-only B: {'PASS' if ok else 'CHECK'} (stopped x={x:.2f}, expect 41.0..42.0 = blocked by the marker square (8,10), bed intact)")


def stage_ghost(e):
    """Hardware bug (2026-10-20): with the only furniture piece in view picked up, its second square kept a solid,
    invisible 0xF031 (the coverage list went stale once nothing was drawn). Table (13,11) facing 1, marker (13,10):
    pick it up from the left, then walk right along row 10 through the old marker square."""
    x, z = walk_until(e, "down", 2, G(0, 11)[1] - 0.7, max_frames=300)
    print(f"  row 11: x={x:.2f} z={z:.2f}")
    x, z = walk_until(e, "right", 0, 44.3, max_frames=200)
    print(f"  facing table anchor: x={x:.2f} z={z:.2f} (13,10)={grid_at(e, 9, 13, 10):#06x}")
    e.press("b", hold=6, after=150)
    print(f"  after B: (13,11)={grid_at(e, 9, 13, 11):#06x} (13,10)={grid_at(e, 9, 13, 10):#06x}")
    walk_until(e, "left", 0, 43.5, max_frames=150)
    x, z = walk_until(e, "up", 2, G(0, 10)[1] + 0.4, max_frames=150)
    print(f"  row 10: x={x:.2f} z={z:.2f}")
    x, z = walk_until(e, "right", 0, 47.0, max_frames=300)
    e.shot("60_ghost_walk")
    mk = grid_at(e, 9, 13, 10)
    ok = x > 46.0 and 58.0 <= z < 59.0 and mk == 0xFFF1 and grid_at(e, 9, 13, 11) == 0xFFF1
    print(f"  RESULT ghost square after pickup: {'PASS' if ok else 'FAIL'} (x={x:.2f} z={z:.2f}, expect x > 46 on row 10; (13,10)={mk:#06x}, expect fff1)")


def find_furniture(e, acre):
    out = []
    for lz in range(16):
        for lx in range(16):
            it = grid_at(e, acre, lx, lz)
            if 0x3000 <= it < 0x4BA4:
                out.append((lx, lz, it))
    return out


def treedrop_main():
    """A furniture tree (id 0x66) two squares south of the door: shaking it drops furniture, which must stay a leaf
    (no model load, no collision). Then the leaf is picked up and dropped again from the pockets: now it is 3D."""
    tree = tile_off(9, 11, 9)
    empty_pockets = {0xC + 0x1B22 + 2 * i: 0xFFF1 for i in range(15)}   # the leaf goes to slot 0
    save = prepare_save(PROJECT / "build" / "test_furniture_tree.sav", edits=dict(bells=50000), grid={tree: 0x0066},
                        pokes=empty_pockets)
    with Emu(ROM_PLUS, str(save), tag="ftrt") as e:
        e.boot_to_town()
        e.wait(300)
        x, z = walk_until(e, "down", 2, 58.0, max_frames=300)
        print(f"  in front of the tree: x={x:.2f} z={z:.2f}")
        before = find_furniture(e, 9)
        e.press("a", hold=6, after=300)
        drops = [d for d in find_furniture(e, 9) if d not in before]
        loads = payload_symbols()["g_ftr_perf"]
        n0 = e.u32(loads)
        e.wait(120)
        e.shot("70_tree_drop")
        n1 = e.u32(loads)
        print(f"  tree drop squares: {[(lx, lz, hex(it)) for lx, lz, it in drops]}, models loaded {n0} -> {n1}")
        leaf = struct.unpack("<8H", e.read(payload_symbols()["s_leaf"], 16))
        print(f"  s_leaf={leaf}")
        ok = len(drops) == 1 and n1 == n0 == 0
        print(f"  RESULT tree-dropped furniture stays a leaf: {'PASS' if ok else 'FAIL'} (drops={len(drops)}, loads {n0}->{n1}, expect 1 drop, 0 loads)")
        walk_until(e, "left", 0, 42.8, max_frames=100)
        walk_until(e, "down", 2, 56.75, max_frames=60)   # (10,8) facing down at the leaf (10,9)
        where(e, "facing the leaf")
        for nudge in ("down", "up", "left"):   # B takes what is underfoot or in front; retry from a nudged spot
            e.press("b", hold=6, after=150)
            left = [d for d in find_furniture(e, 9) if d not in before]
            if not left:
                break
            e.press(nudge, hold=6, after=30)
        print(f"  after B: furniture left from the drop {left}")
        e.press("y", hold=6, after=120)
        e.press("a", hold=6, after=95)
        e.press("down", hold=6, after=40)
        e.press("a", hold=6, after=200)
        e.press("y", hold=6, after=120)
        e.wait(150)
        e.shot("71_dropped_by_player")
        placed = [d for d in find_furniture(e, 9) if d not in before]
        n2 = e.u32(loads)
        print(f"  dropped from the pockets: {placed}, models loaded {n2}")
        ok = not left and len(placed) == 1 and n2 >= 1
        print(f"  RESULT same piece dropped by the player is 3D: {'PASS' if ok else 'FAIL'} (picked up={not left}, placed={len(placed)}, loads={n2})")


def material_emi(e, mdl):
    """Emission (RGB555) of the first material of an NNSG3dResMdl: specEmi high half of the first NNSG3dResMatData."""
    resmat = mdl + e.u32(mdl + 8)
    dict_ = resmat + 4
    info = dict_ + e.u16(dict_ + 6)
    esz = e.u16(info)
    md = resmat + e.u32(info + 4)
    return (e.u32(md + 8) >> 16) & 0x7FFF


def model_emis(e):
    sc = e.u32(payload_symbols()["s_cache"])
    emis = {}
    for i in range(24):
        b = e.read(sc + 72 + i * 232, 24)
        mid = struct.unpack_from("<H", b)[0]
        mdl = struct.unpack_from("<I", b, 20)[0]
        if mid != 0xFFFF and mdl:
            emis[mid] = material_emi(e, mdl)
    return emis


def lamp_crop(path):
    from PIL import Image
    return Image.open(path).crop((96, 192 + 120, 160, 192 + 176))   # town screen, around the lamp below the player


def crop_diff(p1, p2):
    from PIL import ImageChops
    d = ImageChops.difference(lamp_crop(p1).convert("RGB"), lamp_crop(p2).convert("RGB")).convert("L")
    return sum(1 for v in d.getdata() if v > 24)


def lampuse_main(when="night", mode="on"):
    """Exotic lamp two squares south of the door (21:00, or 12:00 with "day"). Walk down against it: A switches
    it off (its shade turns dark: many pixels around the lamp change), A again switches it back on (the lamp looks
    as at the start); the game keeps running (a switch sound once froze it)."""
    pokes = {0x15FB4: struct.pack("<i", 9 * 60)} if when == "night" else {}
    save = prepare_save(PROJECT / "build" / f"test_furniture_lampuse_{when}.sav", edits=dict(bells=50000),
                        grid={tile_off(9, 11, 9): 0x301C}, pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"ftru_{when}") as e:
        e.boot_to_town()
        e.wait(300)
        x, z = walk_until(e, "down", 2, 58.0, max_frames=300)
        e.wait(30)
        print(f"  facing the lamp: x={x:.2f} z={z:.2f}")
        on0 = e.shot("80_lamp_on")
        e.press("a", hold=6, after=60)
        g0 = e.u32(0x021F7E10)
        e.wait(60)
        alive = e.u32(0x021F7E10) - g0
        off = e.shot("81_lamp_switched_off")
        e.press("a", hold=6, after=90)
        on1 = e.shot("82_lamp_switched_on")
        d_off, d_back = crop_diff(on0, off), crop_diff(on0, on1)
        print(f"  pixels changed around the lamp: on->off {d_off}, start->back on {d_back}; "
              f"game frames in 60 vblanks after the first A: {alive}")
        if mode == "off":   # release build: no lamp switching
            ok = d_off < 50 and alive > 10
            print(f"  RESULT release build: A on a lamp changes nothing ({when}): {'PASS' if ok else 'FAIL'}")
            return
        ok = d_off > 300 and d_back < d_off // 4 and alive > 10
        print(f"  RESULT A switches a lamp off and on ({when}): {'PASS' if ok else 'FAIL'}")

def sit_main(piece="chair", mode="on"):
    """Two squares south of the door, the player faces square (11,9). chair: an exotic chair (model 4, facing 3) on
    it. bench: an exotic bench (2-square, facing 1) anchored at (11,10), so (11,9) is its second square (0xF031).
    A with empty hands sits the player there (actions 0x25 -> 0x28, position = the square's centre); Up stands them
    up (0x2C) and puts them back."""
    grid = {tile_off(9, 11, 9): 0x3013} if piece == "chair" else {tile_off(9, 11, 10): 0x300D}
    save = prepare_save(PROJECT / "build" / f"test_furniture_sit_{piece}.sav", edits=dict(bells=50000), grid=grid)
    with Emu(ROM_PLUS, str(save), tag=f"ftrs_{piece}") as e:
        e.boot_to_town()
        e.wait(300)
        x0, z0 = walk_until(e, "down", 2, 58.0, max_frames=300)
        a = player_actor(e)
        e.press("a", hold=6)
        e.wait(8)
        e.shot("89_sitting_down")
        seen = []
        for _ in range(60):
            e.wait(4)
            act = e.u32(a + 0x7EC)
            if not seen or seen[-1] != act:
                seen.append(act)
        x1, _, z1, ang = player_pos(e)
        e.shot("90_sitting")
        g0 = e.u32(0x021F7E10)
        e.wait(30)
        alive = e.u32(0x021F7E10) - g0
        e.press("up", hold=10)
        for _ in range(60):
            e.wait(4)
            act = e.u32(a + 0x7EC)
            if seen[-1] != act:
                seen.append(act)
        x2, _, z2, _ = player_pos(e)
        e.shot("91_stood_up")
        print(f"  stood at ({x0:.2f},{z0:.2f}); sitting at ({x1/8192:.2f},{z1/8192:.2f}) angle={ang:#06x}; "
              f"after Up ({x2/8192:.2f},{z2/8192:.2f}); actions {[hex(v) for v in seen]}; game frames {alive}/30")
        if mode == "off":   # release build: no sitting
            ok = 0x25 not in seen and 0x28 not in seen and alive > 5
            print(f"  RESULT release build: A on a {piece} does not sit: {'PASS' if ok else 'FAIL'}")
            return
        sat = 0x25 in seen and 0x28 in seen and abs(x1 / 8192 - 43.5) < 0.05 and abs(z1 / 8192 - 57.5) < 0.05
        print(f"  RESULT A on a {piece} sits the player on it: {'PASS' if sat and alive > 5 else 'FAIL'}")
        up = 0x2C in seen and seen[-1] not in (0x25, 0x28, 0x2C) and abs(z2 / 8192 - z0) < 0.6
        print(f"  RESULT Up stands the player up from the {piece} where they were: {'PASS' if up else 'FAIL'}")


def ghost_main():
    save = prepare_save(PROJECT / "build" / "test_furniture_ghost.sav",
                        edits=dict(bells=50000), grid={tile_off(9, 13, 11): 0x3015})
    with Emu(ROM_PLUS, str(save), tag="ftrg") as e:
        e.boot_to_town()
        e.wait(210)
        stage_ghost(e)


STAGES = {"marker": stage_marker_only, "pickup": stage_pickup, "collide": stage_collide, "drop": stage_drop, "house": stage_house}


def main():
    if sys.argv[1:] == ["ghost"]:
        return ghost_main()
    if sys.argv[1:2] == ["sit"]:
        return sit_main(*sys.argv[2:4])
    if sys.argv[1:2] == ["lampuse"]:
        return lampuse_main(*sys.argv[2:4])
    if sys.argv[1:] == ["treedrop"]:
        return treedrop_main()
    for lx, lz, it in YARD:
        print(f"yard ({lx},{lz}) {it:#06x} footprint={footprint(it)}")
    save = prepare_save(PROJECT / "build" / "test_furniture.sav",
                        edits=dict(bells=50000, items=POCKETS),
                        grid={**{tile_off(9, lx, lz): it for lx, lz, it in YARD}, tile_off(9, 11, 9): 0xF031})
    with Emu(ROM_PLUS, str(save), tag="ftr") as e:
        e.boot_to_town()
        e.wait(210)
        e.shot("01_yard")
        cache_state(e, "yard")
        for name in (sys.argv[1:] or ["collide"]):
            print(f"== stage {name}")
            STAGES[name](e)


def dbg(e):
    a = payload_symbols()["g_ftr_dbg"]
    return struct.unpack("<4I", e.read(a, 16))


def walk_stage(e):
    def where(label):
        x, y, z, ang = player_pos(e)
        print(f"  [{label}] player x={x/8192:.2f} z={z/8192:.2f} unit=({x>>13},{z>>13}) angle={ang:#06x} dbg={dbg(e)}")
    where("start")
    e.press("down", hold=90, after=10); where("after down")
    e.press("left", hold=150, after=20); where("after left (row 10, towards bed square (8,10))")
    e.shot("02_against_bed")
    print("  grid after walking near the bed:")
    dump_grid(e, 9, 6, 13)


if __name__ == "__main__":
    main()
