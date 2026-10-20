"""Code home state after boot: loader state, export pointers, root-heap free space."""
import struct, sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
syms = payload_symbols()
save = prepare_save(PROJECT / "build" / "probe_hx.sav", edits=dict(bells=50000), grid={0xC354 + 9*512 + (9*16+9)*2: 0x301C})
with Emu(ROM_PLUS, str(save), tag="hx") as e:
    e.boot_to_town(); e.wait(200)
    st = e.u8(syms["s_hx_state"])
    fns = struct.unpack("<3I", e.read(syms["g_hx_fn"], 12))
    print(f"s_hx_state={st} g_hx_fn={[hex(x) for x in fns]} s_cache={e.u32(syms['s_cache']):#x}")
    if fns[0]:
        base = fns[0] & ~1
        print("code at fn0:", e.read(base, 16).hex())
