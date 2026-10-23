#!/usr/bin/env python3
"""Code home (src/code_home.h): src/heap/*.c is an autoload block at 0x0229F9A0, below the moved SDK main arena.
Checks in town, after entering the house and after coming back out: the RAM block equals the built autoload image
(code part; .data/.bss may change), the root heap lies above the reserved block, outdoor furniture models load."""
import struct
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from harness import *  # noqa

BASE, RESERVE = A(0x0229F9A0), 0x2000
BLOB = (BUILD / "extracted" / "arm9" / "hx_autoload.bin").read_bytes()


def check(e, label):
    syms = payload_symbols()
    ram = e.read(BASE, len(BLOB))
    code_ok = ram[:1024] == BLOB[:1024]
    magic = struct.unpack_from("<I", ram)[0] == 0x50485741
    heap = e.u32(A(0x021F7ECC))
    loads = e.u32(syms["g_ftr_perf"])
    print(f"  [{label}] magic={magic} code ok={code_ok} root heap={heap:#x} models loaded={loads}")
    return magic and code_ok and heap >= BASE + RESERVE and loads > 0


def main():
    save = prepare_save(BUILD / "test_code_home.sav", edits=dict(bells=50000),
                        grid={0xC354 + 9 * 512 + (9 * 16 + 9) * 2: 0x301C})
    with Emu(ROM_PLUS, str(save), tag="hx") as e:
        e.boot_to_town()
        e.wait(250)
        ok1 = check(e, "town")
        up = RELEASED & ~(1 << KEY_BITS["up"])
        for _ in range(12):   # into the house (as test_furniture.py house)
            e.c.cmd("keys", mask=up)
            e.wait(22)
            e.c.cmd("keys", mask=up & ~(1 << KEY_BITS["a"]))
            e.wait(3)
        e.c.cmd("keys", mask=RELEASED)
        e.wait(400)
        e.shot("hx_in_house")
        ok_in = struct.unpack_from("<I", e.read(BASE, 4))[0] == 0x50485741
        e.press("down", hold=120, after=500)
        e.wait(250)
        ok2 = check(e, "back in town")
        print(f"  RESULT code home present at boot and used: {'PASS' if ok1 else 'FAIL'}")
        print(f"  RESULT code home intact after a house round trip: {'PASS' if ok_in and ok2 else 'FAIL'}")


if __name__ == "__main__":
    main()
