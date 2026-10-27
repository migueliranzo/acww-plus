#!/usr/bin/env python3
"""
Finds, in another region's vanilla binaries, every EU (ADMP) address AC:WW+ uses, and writes the region's address
table (tools/regions/<code>.py), which tools/build_rom.py --region <name> builds from.

usage: py -3.12 tools/remap_region.py us            (needs vanilla/ADME/extracted: see tools/regions/__init__.py)

Inputs (all EU addresses, kept EU in the sources):
  - tools/patches.py: each patch's address, its expected bytes (read back from the other region) and, for "dptr",
    the vanilla data the pointer pointed at (compared, so a menu list that differs is reported);
  - every address literal in the code of src/*.c, src/*.h, src/heap/*.c (comments stripped);
  - every address literal in tools/harness.py and tools/test_*.py;
  - EXTRA below: addresses the patches imply (branch targets inside "bytes" values, tables).
The build constants (arena-lo literal, autoload base, code home, overlay bases) are worked out from the other
region's own autoload / overlay tables, then checked.

How an address is found:
  code / static data: byte patterns. The EU bytes of a window at the address, with relocated bits masked (Thumb and
     ARM BL/BLX, Thumb/ARM pc-relative loads and ADR, and every word that looks like a RAM pointer), searched in the
     same module of the other region. Several windows (after, before, around) vote; a window counts only when it
     matches once. When none is unique, the candidate nearest the address predicted from neighbouring matches wins.
  BSS / data the code points at: references. Each EU literal word near the address (in any module) is located in
     the other region by the code window before it, and the word found there gives the address (plus the same
     offset). The candidates vote.
Anything with no answer, or with disagreeing votes, is reported and the script exits 1 (the table is still
written, with the unresolved addresses left out, so the build refuses them).
"""
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import regions  # noqa: E402

ADDR_RE = regions.ADDR_RE

# Overlay-range addresses in the sources: which overlay they are in (the ranges of overlays overlap).
OVERLAY_HINTS = {
    0x02208430: "ov003", 0x022085DC: "ov003", 0x022235BC: "ov003", 0x0225DD4C: "ov003",
    0x0222D544: "ov004",
    0x02225420: "ov004", 0x02224E2C: "ov004", 0x0222484C: "ov004", 0x02225330: "ov004", 0x02224C80: "ov004",
    0x022246F8: "ov004", 0x022253CC: "ov004", 0x02224E08: "ov004", 0x022247DC: "ov004", 0x022253EC: "ov004",
    0x02224E18: "ov004", 0x0222481C: "ov004",
    # QOL pack: Blathers (ov047), the pocket grid (ov094), the slot picker (ov101), the pockets screen (ov096)
    0x0225D19C: "ov047", 0x0225D1C4: "ov047", 0x0225D1EC: "ov047", 0x0225DCA8: "ov047", 0x0225DD48: "ov047",
    0x022969A4: "ov094", 0x022969C4: "ov094", 0x02299B54: "ov101",
    0x0229AA50: "ov096", 0x0229AB98: "ov096", 0x0229B77C: "ov096", 0x0229BC4C: "ov096", 0x0229BC80: "ov096",
}
# Addresses the patches imply but do not list.
EXTRA = [
    ("ov003", 0x022212FA),          # target of the "b" written at 0x022212C6 (relative: checked below)
    ("arm9", 0x020CC9B8),           # villager species table (the monkey class bytes are at +0x4B of entries 0x90-0x95)
]
# Branches written as raw bytes: (module, address of the branch, EU target). The distance must be the same.
BYTE_BRANCHES = [("ov003", 0x022212C6, 0x022212FA)]
# Literals that are not addresses in the game's binaries (ranges, ROM-wide constants): kept as they are.
IDENTITY = {0x02000000, 0x02400000}
# Functions whose body differs in a region, so byte matching can't find them (the reference vote then lands on a
# neighbour). Found by hand, from a caller that does match; checked by disassembly.
KNOWN = {
    # The item_info getters (one per record field, each clamping the index to 0x56E) are ordered +1, +0, +2 (byte),
    # +2 (halfword) in the EU. The US games keep +1, +0, +2 (halfword); the +2-byte one (a language attribute) is a
    # "return -1" stub there. The +0 getter's literal is found by that order.
    "us": {0x0206228C: 0x02062024},
    "us1": {0x0206228C: 0x02062090},
}
# Patches with no counterpart in a region (the code they change is not there): the build leaves them out.
ABSENT = {
    "us": {0x020622C8},       # the +2-byte item_info getter's clamp (above)
    "us1": {0x020622C8},
}


strip_c_comments = regions.strip_c_comments


def strip_py_comments(text):
    out = []
    for line in text.splitlines():
        out.append(re.sub(r"#.*$", "", line))
    return "\n".join(out)


def code_literals(paths, stripper):
    found = defaultdict(set)
    for p in paths:
        for m in ADDR_RE.finditer(stripper(p.read_text(encoding="utf-8"))):
            found[int(m.group(0), 16)].add(p.name)
    return found


# --------------------------------------------------------------------------------------------------- masking

def is_ptr(w):
    return 0x01FF8000 <= w < 0x02400000 or 0x027C0000 <= w < 0x02800000


def build_mask(buf):
    """1 = byte may differ between regions (relocated); 0 = must match."""
    n = len(buf)
    mask = bytearray(n)
    for i in range(0, n - 3, 2):
        h1, h2 = struct.unpack_from("<HH", buf, i)
        if (h1 & 0xF800) == 0xF000 and (h2 & 0xF800) in (0xF800, 0xE800):   # Thumb BL / BLX
            mask[i:i + 4] = b"\x01\x01\x01\x01"
    for i in range(0, n - 1, 2):
        h = struct.unpack_from("<H", buf, i)[0]
        if (h & 0xF800) in (0x4800, 0xA000):                                # Thumb ldr rX,[pc,#] / add rX,pc,#
            mask[i] = 1
    for i in range(0, n - 3, 4):
        w = struct.unpack_from("<I", buf, i)[0]
        if is_ptr(w):
            mask[i:i + 4] = b"\x01\x01\x01\x01"
        elif (w >> 24) in (0xEB, 0xFA, 0xFB, 0x0B, 0x1B, 0xAB, 0xBB, 0xCB, 0xDB, 0x8B, 0x9B, 0x2B, 0x3B, 0x4B,
                           0x5B, 0x6B, 0x7B):                                # ARM BL (any cond) / BLX
            mask[i:i + 3] = b"\x01\x01\x01"
        elif (w & 0x0F3F0000) == 0x051F0000 or (w & 0x0FFF0000) in (0x028F0000, 0x024F0000):   # ARM ldr pc / adr
            mask[i] = 1
            mask[i + 1] |= 1
    return mask


class Image:
    """The vanilla modules of one region, with masks."""

    def __init__(self, region):
        self.region = region
        self.mods = regions.vanilla_modules(region)          # {name: (base, bytes, bss_size)}
        self._masks = {}

    def mask(self, mod):
        if mod not in self._masks:
            self._masks[mod] = build_mask(self.mods[mod][1])
        return self._masks[mod]

    def module_at(self, addr, hint=None):
        """(module, offset) holding addr in the loaded image, or (module, None) for its BSS."""
        if hint:
            base, buf, bss = self.mods[hint]
            if base <= addr < base + len(buf):
                return hint, addr - base
            if base + len(buf) <= addr < base + len(buf) + bss:
                return hint, None
            raise ValueError(f"0x{addr:08X} is not in {hint}")
        for name in ("arm9", "autoload2", "itcm", "dtcm"):
            base, buf, bss = self.mods[name]
            if base <= addr < base + len(buf):
                return name, addr - base
        base, buf, bss = self.mods["bss"]
        if base <= addr < base + bss:
            return "bss", None
        return None, None


def pattern(buf, mask, start, end):
    parts = []
    for i in range(start, end):
        parts.append(b"." if mask[i] else re.escape(bytes([buf[i]])))
    return re.compile(b"(?=" + b"".join(parts) + b")", re.S)


def find_window(eu, us, eu_mod, us_mod, off, pre, post, align):
    buf = eu.mods[eu_mod][1]
    mask = eu.mask(eu_mod)
    s, e = off - pre, off + post
    if s < 0 or e > len(buf) or e - s < 8:
        return None
    if sum(1 for i in range(s, e) if not mask[i]) < (e - s) * 0.5:
        return None
    if len(set(buf[i] for i in range(s, e) if not mask[i])) <= 2:      # padding / zeros: says nothing
        return None
    hits = [m.start() + pre for m in pattern(buf, mask, s, e).finditer(us.mods[us_mod][1])
            if (m.start() + pre) % align == off % align]
    return hits


WINDOWS = [(0, 32), (0, 48), (0, 64), (0, 24), (0, 16), (16, 16), (32, 32), (8, 24), (32, 0), (64, 0), (48, 16),
           (0, 96), (0, 128), (64, 64), (128, 0), (0, 256), (128, 128)]


def match_bytes(eu, us, eu_mod, us_mod, off, align=2, predicted=None):
    """Offset in us_mod of EU eu_mod+off, by voting windows. Returns (offset, detail) or (None, detail)."""
    votes = Counter()
    multi = []
    for pre, post in WINDOWS:
        hits = find_window(eu, us, eu_mod, us_mod, off, pre, post, align)
        if hits is None:
            continue
        if len(hits) == 1:
            votes[hits[0]] += 1
        elif hits:
            multi.append(hits)
    if votes:
        (best, n), *rest = votes.most_common()
        others = sum(c for _, c in rest)
        if n > others:
            return best, f"bytes {n} window(s)" + (f", {others} disagreeing" if others else "")
        return None, f"windows disagree: {dict((hex(k), v) for k, v in votes.items())}"
    if multi and predicted is not None:
        cands = Counter(h for hits in multi for h in hits)
        best = min(cands, key=lambda h: abs(h - predicted))
        if abs(best - predicted) < 0x200:
            return best, f"bytes, {len(cands)} candidates, nearest to the prediction (+{best - predicted:#x})"
    return None, "no unique window" + (f" ({len(multi)} ambiguous)" if multi else "")


class Remapper:
    def __init__(self, region):
        self.region = region
        self.eu = Image("eu")
        self.us = Image(region)
        self.ovmap = regions.overlay_map(region)
        self.found = {}          # eu addr -> (us addr, detail)
        self.problems = []
        self._literal_index = None

    def us_mod(self, eu_mod):
        if eu_mod.startswith("ov"):
            n = self.ovmap.get(int(eu_mod[2:]))
            if n is None:
                raise KeyError(f"{eu_mod} has no counterpart")
            return f"ov{n:03d}"
        return eu_mod

    def predict(self, eu_mod, off):
        """Offset predicted from the nearest addresses already found in the same module."""
        base = self.eu.mods[eu_mod][0]
        us_base = self.us.mods[self.us_mod(eu_mod)][0]
        best = None
        for a, (u, _) in self.found.items():
            if base <= a < base + len(self.eu.mods[eu_mod][1]) and us_base <= u < us_base + len(
                    self.us.mods[self.us_mod(eu_mod)][1]):
                d = abs(a - base - off)
                if best is None or d < best[0]:
                    best = (d, (u - us_base) - (a - base))
        return off + best[1] if best else None

    def code(self, eu_addr, mod=None, thumb=True):
        """An address inside a module's loaded bytes (code or static data)."""
        mod, off = self.eu.module_at(eu_addr, mod)
        if off is None:
            return self.ram(eu_addr, mod)
        um = self.us_mod(mod)
        align = 2 if thumb else 4
        res, detail = match_bytes(self.eu, self.us, mod, um, off, align)
        if res is None:
            pred = self.predict(mod, off)
            res, detail = match_bytes(self.eu, self.us, mod, um, off, align, pred)
        if res is None:
            ram, rdetail = self.ram(eu_addr, mod, quiet=True)
            if ram is not None:
                return ram, rdetail
            return None, f"{mod}+0x{off:X}: {detail}"
        return self.us.mods[um][0] + res, f"{mod}: {detail}"

    def literal_index(self):
        """{word value: [(module, offset)]} of every aligned pointer-looking word in the EU binaries."""
        if self._literal_index is None:
            idx = defaultdict(list)
            for mod, (base, buf, _) in self.eu.mods.items():
                if mod == "bss":
                    continue
                for i in range(0, len(buf) - 3, 4):
                    w = struct.unpack_from("<I", buf, i)[0]
                    if is_ptr(w):
                        idx[w].append((mod, i))
            self._literal_index = idx
        return self._literal_index

    def ram(self, eu_addr, hint=None, quiet=False):
        """An address the code points at (BSS, data): vote over the EU literals at or just below it."""
        idx = self.literal_index()
        for lo, hi in ((0x40, 0x40), (0x400, 0x40), (0x4000, 0x40)):
            votes = Counter()
            used = 0
            for w in sorted(idx, key=lambda w: abs(w - eu_addr)):
                if not (eu_addr - lo <= w <= eu_addr + hi):
                    continue
                refs = idx[w]
                if hint and hint.startswith("ov"):      # overlay ranges overlap: only the overlay's own references
                    refs = [x for x in refs if x[0] == hint]
                for mod, off in refs[:40]:
                    try:
                        um = self.us_mod(mod)
                    except KeyError:
                        continue
                    if um not in self.us.mods:
                        continue
                    # the code before the literal (its function) locates it
                    for pre, post in ((64, 4), (32, 4), (96, 4), (32, 36), (16, 20)):
                        hits = find_window(self.eu, self.us, mod, um, off, pre, post, 4)
                        if hits and len(hits) == 1:
                            uw = struct.unpack_from("<I", self.us.mods[um][1], hits[0])[0]
                            if is_ptr(uw):
                                votes[(uw - w) + eu_addr] += 1
                                used += 1
                            break
                if used >= 24:
                    break
            if votes:
                (best, n), *rest = votes.most_common()
                others = sum(c for _, c in rest)
                if n >= 2 * others or (n >= 1 and not others):
                    return best, f"refs {n} vote(s) within -0x{lo:X}" + (f", {others} other" if others else "")
                if not quiet:
                    return None, "refs disagree: " + ", ".join(f"0x{k:08X}x{v}" for k, v in votes.most_common(4))
        return None, "no reference found"

    def add(self, eu_addr, how, *args, **kw):
        if eu_addr in self.found:
            return self.found[eu_addr][0]
        if eu_addr in IDENTITY:
            self.found[eu_addr] = (eu_addr, "identity")
            return eu_addr
        known = KNOWN.get(self.region, {})
        if eu_addr in known:
            self.found[eu_addr] = (known[eu_addr], "known (remap_region.KNOWN)")
            return known[eu_addr]
        res, detail = how(eu_addr, *args, **kw)
        if res is None:
            self.problems.append(f"0x{eu_addr:08X}: {detail}")
        else:
            self.found[eu_addr] = (res, detail)
        return res


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "us"
    info = regions.REGIONS[region]
    r = Remapper(region)
    from patches import PATCHES

    # 1. patches (module known)
    patch_out = {}
    for mod, addr, kind, expect, value, note in PATCHES:
        if addr in ABSENT.get(region, ()):
            patch_out[addr] = None
            continue
        thumb = kind in ("bl",) or (kind == "bytes" and len(expect) == 4)
        u = r.add(addr, r.code, mod, thumb=thumb if kind != "ptr" and kind != "dptr" else False)
        if u is None:
            continue
        um = r.us_mod(mod)
        base, buf, _ = r.us.mods[um]
        got = buf[u - base: u - base + len(expect) // 2].hex()
        patch_out[addr] = (um, u, got)
        if kind == "bytes":
            # the bytes replaced must be the same, except relocated bits (a BL's offset, a pointer)
            emask = r.eu.mask(mod)
            eoff = addr - r.eu.mods[mod][0]
            exp = bytes.fromhex(expect)
            if any(exp[i] != bytes.fromhex(got)[i] and not emask[eoff + i] for i in range(len(exp))):
                r.problems.append(f"patch 0x{addr:08X} ({note}): EU bytes {expect}, other region {got}")
        if kind == "dptr":
            # the vanilla data the pointer pointed at must be the same
            ep = int.from_bytes(bytes.fromhex(expect), "little")
            up = int.from_bytes(bytes.fromhex(got), "little")
            em, eo = r.eu.module_at(ep, mod)
            ed = r.eu.mods[em][1][eo: eo + 8]
            ud = buf[up - base: up - base + 8]
            ew, en = struct.unpack("<II", ed)
            uw, un = struct.unpack("<II", ud)
            if is_ptr(ew) and is_ptr(uw) and en == un:      # {list pointer, count}: compare the lists
                em2, eo2 = r.eu.module_at(ew, mod)
                ed, ud = r.eu.mods[em2][1][eo2: eo2 + en], buf[uw - base: uw - base + un]
            if ed != ud:
                r.problems.append(f"dptr 0x{addr:08X}: pointed data EU {ed.hex()} vs {ud.hex()}")
        if kind == "ptr":
            ep = int.from_bytes(bytes.fromhex(expect), "little") & ~1
            up = int.from_bytes(bytes.fromhex(got), "little") & ~1
            if ep in OVERLAY_HINTS or True:
                r.found.setdefault(ep, (up, f"read from the action table at 0x{u:08X}"))

    for mod, addr in EXTRA:
        r.add(addr, r.code, mod, thumb=False)
    for mod, at, target in BYTE_BRANCHES:
        if at in r.found and target in r.found and r.found[target][0] - r.found[at][0] != target - at:
            r.problems.append(f"branch at 0x{at:08X}: distance to 0x{target:08X} differs")

    # 2. sources and tests
    srcs = sorted((ROOT / "src").glob("*.c")) + sorted((ROOT / "src").glob("*.h")) + sorted(
        (ROOT / "src" / "heap").glob("*.c"))
    lits = code_literals(srcs, strip_c_comments)
    tests = [ROOT / "tools" / "harness.py"] + sorted((ROOT / "tools").glob("test_*.py"))
    tlits = code_literals(tests, strip_py_comments)
    allx = dict(lits)
    for k, v in tlits.items():
        allx.setdefault(k, set()).update(v)
    consts = regions.build_constants(region)
    eu_consts = regions.build_constants("eu")
    for a in sorted(allx):
        if a in IDENTITY:
            r.found[a] = (a, "identity")
            continue
        if a == eu_consts["HEAP_CODE_BASE"]:
            r.found[a] = (consts["HEAP_CODE_BASE"], "code home base (end of the highest overlay)")
            continue
        if a in OVERLAY_HINTS:
            r.add(a, r.code, OVERLAY_HINTS[a], thumb=True)
        else:
            mod, off = r.eu.module_at(a)
            if mod is None:
                r.problems.append(f"0x{a:08X}: not in arm9 / autoloads / main BSS and no overlay hint "
                                  f"({', '.join(sorted(allx[a]))})")
                continue
            r.add(a, r.code, None, thumb=bool(a & 1) or True)

    # two patches on one address: one of them was mapped wrong
    seen = {}
    for a, p in patch_out.items():
        if p is not None and p[:2] in seen:
            r.problems.append(f"patches 0x{seen[p[:2]]:08X} and 0x{a:08X} both map to {p[0]} 0x{p[1]:08X}")
        elif p is not None:
            seen[p[:2]] = a

    # 3. build constants: check the arena literal of the other region
    au = r.us.mods["autoload2"]
    lit = consts["ARENA_LO_LITERAL"]
    if struct.unpack_from("<I", au[1], lit - au[0])[0] != consts["HEAP_CODE_BASE"]:
        r.problems.append(f"arena lo literal 0x{lit:08X} does not hold 0x{consts['HEAP_CODE_BASE']:08X}")
    m = r.found.get(eu_consts["ARENA_LO_LITERAL"])
    if m is None:
        r.add(eu_consts["ARENA_LO_LITERAL"], r.code, "autoload2", thumb=False)
        m = r.found.get(eu_consts["ARENA_LO_LITERAL"])
    if m and m[0] != lit:
        r.problems.append(f"arena lo literal: pattern says 0x{m[0]:08X}, the table scan 0x{lit:08X}")

    # 4. write
    out = ROOT / "tools" / "regions" / f"{info['table']}.py"
    lines = [f'"""Address table for {info["title"]} ({info["code"]}), generated by tools/remap_region.py {region}.',
             "Do not edit by hand: change the EU sources or the hints in tools/remap_region.py and rerun.", '"""', "",
             "# EU address -> this region's address  (how it was found)", "ADDR = {"]
    for a in sorted(r.found):
        u, d = r.found[a]
        lines.append(f"    0x{a:08X}: 0x{u:08X},   # {d}")
    lines += ["}", "", "# patch address (EU) -> vanilla bytes at the mapped address in this region (None: no counterpart, "
              "remap_region.ABSENT)", "PATCH_EXPECT = {"]
    for a in sorted(patch_out):
        lines.append(f"    0x{a:08X}: None," if patch_out[a] is None else f"    0x{a:08X}: \"{patch_out[a][2]}\",")
    lines += ["}", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {len(r.found)} addresses, {len(patch_out)} of {len(PATCHES)} patches"
          f" ({sum(p is None for p in patch_out.values())} with no counterpart)")
    for k, v in consts.items():
        print(f"  {k:18s} EU 0x{eu_consts[k]:08X} -> 0x{v:08X}")
    if r.problems:
        print(f"\n{len(r.problems)} problem(s):")
        for p in r.problems:
            print("  " + p)
        sys.exit(1)
    print("all addresses found")


if __name__ == "__main__":
    main()
