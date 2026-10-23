#!/usr/bin/env python3
"""
Makes the release patch: a BPS patch from the clean ROM to the release build, checks it by applying it again, and
writes the hashes players need.

usage: py -3.12 tools/make_patch.py [VERSION] [--region eu|us]          (default version "alpha", region eu)
  eu -> build/release/acww_plus_<VERSION>.bps, hashes.txt, README.md (docs/release/README.md),
        from build/acww_plus_release.nds
  us -> build/release/acww_plus_<VERSION>_us.bps, hashes_us.txt, README_US.md (docs/release/README_US.md),
        from build/us/acww_plus_release.nds (tools/build_rom.py --release --region us)

BPS (byuu's format) stores the source and target CRC32, so patchers refuse a wrong base ROM. Players apply it with
Rom Patcher JS (web), Flips or beat. The encoder is a plain greedy one: it follows the current source offset while
bytes match (most of the ROM is the vanilla data at a shifted position), and looks a new offset up in a block index
when the match ends.
"""
import hashlib
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import regions  # noqa: E402

REGION = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "eu"
INFO = regions.REGIONS[REGION]
CLEAN_ROM = INFO["clean_rom"]
TARGET_ROM = regions.build_dir(ROOT, REGION) / "acww_plus_release.nds"
OUT_DIR = ROOT / "build" / "release"
SUFFIX = INFO["suffix"]                     # "" (EU), "_us"
README = "README.md" if REGION == "eu" else f"README{SUFFIX.upper()}.md"

BLOCK = 32          # bytes per index block (source, aligned)
MIN_MATCH = 32      # shorter matches are written as literal bytes


def enc_num(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def dec_num(b, i):
    data, shift = 0, 1
    while True:
        x = b[i]
        i += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, i
        shift <<= 7
        data += shift


def match_len(a, ai, b, bi):
    """Length of the common run of a[ai:] and b[bi:]."""
    n = 0
    step = 1 << 16
    lim = min(len(a) - ai, len(b) - bi)
    while n < lim:
        s = min(step, lim - n)
        if a[ai + n: ai + n + s] == b[bi + n: bi + n + s]:
            n += s
            continue
        if s == 1:
            break
        step = max(1, s // 16)
    return n


def build_index(src):
    idx = {}
    for p in range(0, len(src) - BLOCK + 1, BLOCK):
        idx.setdefault(hash(src[p:p + BLOCK]), p)
    return idx


def make_bps(src, tgt):
    idx = build_index(src)
    out = bytearray(b"BPS1" + enc_num(len(src)) + enc_num(len(tgt)) + enc_num(0))
    t = 0
    off = 0                 # current source - target offset
    src_rel = 0             # BPS sourceRelativeOffset
    lit = bytearray()

    def flush_literal():
        if lit:
            out.extend(enc_num(((len(lit) - 1) << 2) | 1))
            out.extend(lit)
            lit.clear()

    while t < len(tgt):
        s = t + off
        n = match_len(tgt, t, src, s) if 0 <= s < len(src) else 0
        if n < MIN_MATCH:
            n = 0
            for d in range(BLOCK):
                if t + d + BLOCK > len(tgt):
                    break
                p = idx.get(hash(tgt[t + d: t + d + BLOCK]))
                if p is None or p - d < 0:
                    continue
                m = match_len(tgt, t, src, p - d)
                if m >= MIN_MATCH:
                    off, s, n = p - d - t, p - d, m
                    break
        if n < MIN_MATCH:
            lit.append(tgt[t])
            t += 1
            continue
        flush_literal()
        if s == t:
            out.extend(enc_num(((n - 1) << 2) | 0))              # SourceRead
        else:
            rel = s - src_rel
            out.extend(enc_num(((n - 1) << 2) | 2))              # SourceCopy
            out.extend(enc_num((abs(rel) << 1) | (1 if rel < 0 else 0)))
            src_rel = s + n
        t += n
    flush_literal()
    out.extend(struct.pack("<II", zlib.crc32(src), zlib.crc32(tgt)))
    out.extend(struct.pack("<I", zlib.crc32(out)))
    return bytes(out)


def apply_bps(src, patch):
    assert patch[:4] == b"BPS1"
    ssz, i = dec_num(patch, 4)
    tsz, i = dec_num(patch, i)
    msz, i = dec_num(patch, i)
    i += msz
    assert ssz == len(src) and struct.unpack_from("<I", patch, len(patch) - 12)[0] == zlib.crc32(src)
    out = bytearray(tsz)
    o = src_rel = tgt_rel = 0
    end = len(patch) - 12
    while i < end:
        d, i = dec_num(patch, i)
        cmd, n = d & 3, (d >> 2) + 1
        if cmd == 0:
            out[o:o + n] = src[o:o + n]
        elif cmd == 1:
            out[o:o + n] = patch[i:i + n]
            i += n
        else:
            r, i = dec_num(patch, i)
            r = -(r >> 1) if r & 1 else r >> 1
            if cmd == 2:
                src_rel += r
                out[o:o + n] = src[src_rel:src_rel + n]
                src_rel += n
            else:
                tgt_rel += r
                for k in range(n):
                    out[o + k] = out[tgt_rel + k]
                tgt_rel += n
        o += n
    assert zlib.crc32(out) == struct.unpack_from("<I", patch, len(patch) - 8)[0], "target CRC mismatch"
    return bytes(out)


def hashes(label, data):
    return (f"{label}\n  size  {len(data)} bytes\n  CRC32 {zlib.crc32(data):08X}\n"
            f"  MD5   {hashlib.md5(data).hexdigest()}\n  SHA-1 {hashlib.sha1(data).hexdigest()}\n")


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if a != "--region" and sys.argv[i - 1] != "--region"]
    version = args[0] if args else "alpha"
    src = CLEAN_ROM.read_bytes()
    tgt = TARGET_ROM.read_bytes()
    if src[0x0C:0x10] != INFO["code"].encode():
        raise SystemExit(f"{CLEAN_ROM} is not the {INFO['title']} ROM (game code {src[0x0C:0x10]!r}, "
                         f"expected {INFO['code']})")
    if zlib.crc32(src) != INFO["clean_crc32"]:
        raise SystemExit(f"{CLEAN_ROM}: CRC32 {zlib.crc32(src):08X}, expected {INFO['clean_crc32']:08X}")
    patch = make_bps(src, tgt)
    if apply_bps(src, patch) != tgt:
        raise SystemExit("self-check failed: the patch does not rebuild the release ROM")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"acww_plus_{version}{SUFFIX}.bps"
    out.write_bytes(patch)
    hashes_txt = OUT_DIR / f"hashes{SUFFIX}.txt"
    hashes_txt.write_text(
        hashes(f"Clean ROM to patch: {INFO['title']} (game code {INFO['code']})", src) + "\n" +
        hashes(f"Patched ROM (AC:WW+ {version}{SUFFIX})", tgt) + "\n" + hashes(f"Patch file {out.name}", patch),
        encoding="utf-8")
    (OUT_DIR / README).write_bytes((ROOT / "docs" / "release" / README).read_bytes())
    print(f"{out} ({len(patch):,} bytes), self-check passed; {README} copied")
    print(hashes_txt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
