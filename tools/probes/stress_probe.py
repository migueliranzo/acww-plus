"""Stress: N distinct furniture models around the house (acre 9 rows 7-12). Reports loaded models, VRAM used,
polygon / vertex counts and game frame rate. usage: stress_probe.py [N] [rom] [port]"""
import struct, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
from PIL import Image
n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
rom = sys.argv[2] if len(sys.argv) > 2 else ROM_PLUS
port = int(sys.argv[3]) if len(sys.argv) > 3 else 19889
always = open(PROJECT / "build" / "extracted" / "files" / "ftr_info" / "ENG" / "always.bin", "rb").read()
models = [m for m in range(0x20, 0x6E9) if always[m * 8 + 5] == 0][:n]   # 1x1 pieces, distinct models
free = [(lx, lz) for lz in (8, 9, 10, 11, 12, 13) for lx in range(3, 16) if (lx, lz) not in ((11, 8),)]
orig = open(VANILLA_SAV, "rb").read()
grid = {}
for (lx, lz) in free:
    if len(grid) >= n: break
    off = 0xC354 + 9 * 512 + (lz * 16 + lx) * 2
    if struct.unpack_from("<H", orig, off)[0] == 0xFFF1:
        grid[off] = 0x3000 + models[len(grid)] * 4
save = prepare_save(PROJECT / "build" / f"probe_stress{n}.sav", grid=grid)
with Emu(rom, str(save), port=port, tag=f"stress{n}") as e:
    e.boot_to_town(); e.wait(400)
    walk_until(e, "down", 2, 59.0, max_frames=200)
    e.wait(200)
    sc = e.u32(payload_symbols()["s_cache"]) if rom == ROM_PLUS else 0
    loaded = used = 0
    if sc:
        for i in range(24):
            mid, ar, dist, off, sz = struct.unpack("<HBBHH", e.read(sc + 72 + i * 200, 8))
            if mid != 0xFFFF: loaded += 1; used += sz
    a = e.u32(0x021F7E10); pmax = vmax = 0
    for k in range(60):
        e.wait(5)
        r = e.c.cmd("read_io", cpu=9, addr=0x04000604, width=32)["value"]
        pmax = max(pmax, r & 0xFFF); vmax = max(vmax, (r >> 16) & 0x1FFF)
    b = e.u32(0x021F7E10)
    hf = e.u32(sc + 0x14) if sc else 0
    print(f"  heap largest free block at last load={hf:#x}")
    print(f"  pieces placed={len(grid)} models loaded={loaded} tex VRAM used={used:#x}  polys max={pmax} verts max={vmax}  game frames/300vbl={b - a}")
    p = e.shot("stress")
Image.open(p).convert("RGB").crop((0, 192, 256, 384)).resize((512, 384), Image.NEAREST).save(str(p).replace(".png", "_zoom.png"))
