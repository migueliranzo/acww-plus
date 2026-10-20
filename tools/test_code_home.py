#!/usr/bin/env python3
"""Code home (src/code_home.c): /zplus/code.bin is loaded into the root heap, relocated, and its exports are used.
Checks after boot, after entering the house and after coming back out: loader state 1, the in-RAM image equals the
file image with the relocations applied, export pointers inside the image, outdoor furniture models loaded."""
import struct
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa

BLOB = (PROJECT / "build" / "extracted" / "files" / "zplus" / "code.bin").read_bytes()


def check(e, label):
    syms = payload_symbols()
    st = e.u8(syms["s_hx_state"])
    n_exp, n_rel = struct.unpack_from("<2I", BLOB, 8)
    size = struct.unpack_from("<I", BLOB, 4)[0]
    fns = struct.unpack(f"<{n_exp}I", e.read(syms["g_hx_fn"], 4 * n_exp))
    exp_offs = struct.unpack_from(f"<{n_exp}I", BLOB, 16)
    rel_offs = struct.unpack_from(f"<{n_rel}I", BLOB, 16 + 4 * n_exp)
    img_file = bytearray(BLOB[16 + 4 * (n_exp + n_rel):])
    base = (fns[0] & ~1) - (exp_offs[0] & ~1) if fns[0] else 0
    for o in rel_offs:
        struct.pack_into("<I", img_file, o, (struct.unpack_from("<I", img_file, o)[0] + base) & 0xFFFFFFFF)
    # .data / .bss change at run time: compare every relocated word and the first 1 KB (code)
    ram = e.read(base, size) if base else b""
    same_rel = all(ram[o:o + 4] == img_file[o:o + 4] for o in rel_offs) if ram else False
    same_code = ram[:1024] == bytes(img_file[:1024]) if ram else False
    in_img = all(base <= (f & ~1) < base + size for f in fns) if base else False
    loads = e.u32(syms["g_ftr_perf"])
    print(f"  [{label}] state={st} base={base:#x} size={size} exports in image={in_img} relocs ok={same_rel} "
          f"code ok={same_code} models loaded={loads}")
    return st == 1 and in_img and same_rel and same_code and loads > 0, base


def main():
    save = prepare_save(PROJECT / "build" / "test_code_home.sav", edits=dict(bells=50000),
                        grid={0xC354 + 9 * 512 + (9 * 16 + 9) * 2: 0x301C})
    with Emu(ROM_PLUS, str(save), tag="hx") as e:
        e.boot_to_town()
        e.wait(250)
        ok1, b1 = check(e, "town")
        up = RELEASED & ~(1 << KEY_BITS["up"])
        for _ in range(12):   # into the house (as test_furniture.py house)
            e.c.cmd("keys", mask=up)
            e.wait(22)
            e.c.cmd("keys", mask=up & ~(1 << KEY_BITS["a"]))
            e.wait(3)
        e.c.cmd("keys", mask=RELEASED)
        e.wait(400)
        e.shot("hx_in_house")
        e.press("down", hold=120, after=500)
        e.wait(250)
        ok2, b2 = check(e, "back in town")
        print(f"  RESULT code home loaded, relocated and used: {'PASS' if ok1 else 'FAIL'}")
        print(f"  RESULT code home survives a house round trip: {'PASS' if ok2 and b1 == b2 else 'FAIL'}")


if __name__ == "__main__":
    main()
