"""Boot to town on the plus ROM and print u32 values at the given addresses."""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
addrs = [int(a, 16) for a in sys.argv[1:]]
save = prepare_save(PROJECT / "build" / "probe_peek.sav")
with Emu(ROM_PLUS, str(save), port=19898, tag="peek") as e:
    e.boot_to_town(); e.wait(60)
    for a in addrs:
        print(hex(a), hex(e.u32(a)))
