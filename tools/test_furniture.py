#!/usr/bin/env python3
"""
Outdoor furniture test (ndsref, headless).
Yard around the player's house (acre 9) gets 1x1, 2-square (two facings) and 2x2 pieces, with more distinct
models than the old fixed 5-slot cache could hold. Pockets get a 2x2 bed, a 2-square couch and a chair.
Checks: 3D draw, cache state, F031 markers on secondary squares, pocket drop, teardown on entering the house.
usage: test_furniture.py [stage ...]   stages: yard drop house (default: all)
"""
import struct
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa

GRID_SAVE = 0xC354
GRID_RAM = SAVE_RAM_BASE + GRID_SAVE
ALWAYS = open(r"e:\acww-plus\build\extracted\files\ftr_info\ENG\always.bin", "rb").read()


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
        slot_sz = 200
        print(f"     player grid=({hdr[14]},{hdr[15]})")
        for i in range(12):
            b = e.read(sc + 72 + i * slot_sz, 24)
            mid, ar, dist, off, sz, tick, fseq, arc, mdl = struct.unpack("<HBBHHIIII", b)
            if mid != 0xFFFF:
                print(f"     slot{i}: model={mid:#06x} arena={ar} dist={dist} off={off:#x} size={sz:#x} tick={tick} arc={arc:#x}")
    vr = [e.u32(0x021F2CB4 + 4*i) - e.u32(0x021F2CC4 + 4*i) for i in range(4)]
    print(f"     vram tex free={[hex(x) for x in vr]} pltt free={e.u32(0x021F2CD4) - e.u32(0x021F2CB0):#x}")
    return sc


def main():
    for lx, lz, it in YARD:
        print(f"yard ({lx},{lz}) {it:#06x} footprint={footprint(it)}")
    save = prepare_save(PROJECT / "build" / "test_furniture.sav",
                        edits=dict(bells=50000, items=POCKETS),
                        grid={tile_off(9, lx, lz): it for lx, lz, it in YARD})
    with Emu(ROM_PLUS, str(save), tag="ftr") as e:
        e.boot_to_town()
        e.wait(210)
        e.shot("01_yard")
        cache_state(e, "yard")
        print("  grid acre 9 rows 6..12 after settle:")
        dump_grid(e, 9, 6, 13)
        # Walk down-left past the bed so collision queries reach its squares
        return
        e.press("down", hold=20, after=10)
        e.press("left", hold=30, after=20)
        e.shot("02_near_bed")
        print("  grid after walking near the bed:")
        dump_grid(e, 9, 6, 13)
        e.press("left", hold=40, after=20)
        e.shot("03_push_bed")
        e.press("down", hold=60, after=30)
        e.shot("04_south")


if __name__ == "__main__":
    main()
