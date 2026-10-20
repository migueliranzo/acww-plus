#!/usr/bin/env python3
"""
Builds the AC:WW+ ROM (e:/acww-plus/build/acww_plus.nds).

1. Compiles every src/*.c as one unit (build/acww_plus_unity.c) with Metrowerks mwccarm.exe.
2. Links the ELF object at 0x01FFDC00 (unused ITCM tail) and writes build/payload.map.
3. Copies fresh vanilla arm9/overlay binaries from E:/claudeGameDecomp/extracted (read only), appends the
   payload to itcm.bin, and applies tools/patches.py (each patch checks the vanilla bytes first).
4. Runs dsd rom build.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT_DIR = Path(r"e:\acww-plus")
UNITY_C = ROOT_DIR / "build" / "acww_plus_unity.c"
OBJ_O = ROOT_DIR / "build" / "acww_plus.o"
PAYLOAD_BIN = ROOT_DIR / "build" / "payload_itcm.bin"
EXTRACTED_DIR = ROOT_DIR / "build" / "extracted"
OUT_ROM = ROOT_DIR / "build" / "acww_plus.nds"

VANILLA_EXTRACTED = Path(r"E:\claudeGameDecomp\extracted")
DSD_EXE = Path(r"E:\claudeGameDecomp\dsd-windows-x86_64.exe")
MWCCARM_EXE = Path(r"C:\NDS_RECOMP\nds-docs\pokemon_dp\sdk\cw\ARM_Tools\Command_Line_Tools\mwccarm.exe")

ITCM_BASE_ADDR = 0x01FF8000
PAYLOAD_OFFSET_IN_ITCM = 0x5C00
PAYLOAD_BASE_ADDR = ITCM_BASE_ADDR + PAYLOAD_OFFSET_IN_ITCM  # 0x01FFDC00
ITCM_END_ADDR = 0x02000000

ARM9_BASE_ADDR = 0x02000000
OV003_BASE_ADDR = 0x02207F60


def encode_thumb_bl(src_addr: int, target_addr: int) -> bytes:
    """Encodes a 4-byte Thumb BL instruction from src_addr to target_addr."""
    rel = (target_addr & ~1) - (src_addr + 4)
    if rel < -0x400000 or rel >= 0x400000 or (rel & 1):
        raise ValueError(f"Thumb BL out of range: 0x{src_addr:08X} -> 0x{target_addr:08X}")
    imm22 = (rel >> 1) & 0x3FFFFF
    hi11 = (imm22 >> 11) & 0x7FF
    lo11 = imm22 & 0x7FF
    hw1 = 0xF000 | hi11
    hw2 = 0xF800 | lo11
    return struct.pack("<HH", hw1, hw2)


def compile_c_source(unity=None, obj=None):
    unity = unity or UNITY_C
    obj = obj or OBJ_O
    cmd = [
        str(MWCCARM_EXE),
        "-O4,s",
        "-inline", "off",
        "-proc", "arm946e",
        "-thumb",
        "-interworking",
        "-c", str(unity),
        "-o", str(obj),
    ]
    env = os.environ.copy()
    env["MWCIncludes"] = str(ROOT_DIR / "src")
    env["LM_LICENSE_FILE"] = str(MWCCARM_EXE.parents[2] / "license.dat")
    print(f"[1/4] Compiling {unity.name} with mwccarm.exe...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)


def link_elf_object(obj_path: Path, base_addr: int, externs=None, relocs_out=None):
    """externs: {name: address} for symbols defined outside the object (heap code -> ITCM payload).
    relocs_out: list that receives the image offsets of ABS32 words pointing inside the image (heap code)."""
    data = obj_path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError("Not a valid ELF file")

    e_shoff, = struct.unpack_from("<I", data, 0x20)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x2E)

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = (
            struct.unpack_from("<10I", data, off)
        )
        sections.append({
            "idx": i,
            "sh_name": sh_name,
            "type": sh_type,
            "flags": sh_flags,
            "offset": sh_offset,
            "size": sh_size,
            "link": sh_link,
            "info": sh_info,
            "align": max(sh_addralign, 4),
            "entsize": sh_entsize,
            "content": bytearray(data[sh_offset : sh_offset + sh_size]) if sh_type != 8 else bytearray(sh_size),
        })

    shstr = bytes(sections[e_shstrndx]["content"])
    for s in sections:
        end = shstr.find(b"\x00", s["sh_name"])
        s["name"] = shstr[s["sh_name"]:end].decode("ascii", errors="replace")

    # Lay out allocatable sections (.text, .rodata, .data, .bss)
    cur_addr = base_addr
    alloc_order = [".text", ".rodata", ".data", ".bss"]
    sec_by_name = {}
    for name in alloc_order:
        for s in sections:
            if s["name"] == name and (s["flags"] & 0x2):  # SHF_ALLOC
                align = max(s["align"], 4)
                cur_addr = (cur_addr + align - 1) & ~(align - 1)
                s["vaddr"] = cur_addr
                cur_addr += s["size"]
                sec_by_name[name] = s

    # Also catch any other SHF_ALLOC sections if present
    for s in sections:
        if (s["flags"] & 0x2) and "vaddr" not in s:
            align = max(s["align"], 4)
            cur_addr = (cur_addr + align - 1) & ~(align - 1)
            s["vaddr"] = cur_addr
            cur_addr += s["size"]

    total_size = (cur_addr - base_addr + 3) & ~3

    # Parse symbol table
    symtab_sec = next(s for s in sections if s["type"] == 2)  # SHT_SYMTAB
    strtab_sec = sections[symtab_sec["link"]]
    strtab = bytes(strtab_sec["content"])
    sym_bytes = bytes(symtab_sec["content"])
    num_syms = len(sym_bytes) // 16

    symbols = []
    sym_addrs = {}
    for i in range(num_syms):
        st_name, st_value, st_size, st_info, st_other, st_shndx = struct.unpack_from("<IIIBBH", sym_bytes, i * 16)
        end = strtab.find(b"\x00", st_name)
        name = strtab[st_name:end].decode("ascii", errors="replace")
        vaddr = st_value
        if 0 < st_shndx < len(sections) and "vaddr" in sections[st_shndx]:
            vaddr += sections[st_shndx]["vaddr"]
        elif st_shndx == 0 and i > 0:
            if externs is None or name not in externs:
                raise ValueError(f"Undefined external symbol in object: {name}")
            vaddr = externs[name]
        symbols.append({"name": name, "vaddr": vaddr, "info": st_info, "shndx": st_shndx, "size": st_size,
                        "external": st_shndx == 0 and i > 0})
        if name:
            sym_addrs[name] = vaddr

    # Apply SHT_RELA (type 4) and SHT_REL (type 9) relocations
    for s in sections:
        if s["type"] not in (4, 9):
            continue
        target_sec = sections[s["info"]]
        if "vaddr" not in target_sec:
            continue
        t_buf = target_sec["content"]
        t_base = target_sec["vaddr"]
        is_rela = (s["type"] == 4)
        ent_sz = 12 if is_rela else 8
        raw = bytes(s["content"])
        for off in range(0, len(raw), ent_sz):
            if is_rela:
                r_offset, r_info, r_addend = struct.unpack_from("<IIi", raw, off)
            else:
                r_offset, r_info = struct.unpack_from("<II", raw, off)
                r_addend = 0
            r_sym = r_info >> 8
            r_type = r_info & 0xFF
            sym = symbols[r_sym]
            S = sym["vaddr"]
            P = t_base + r_offset

            if r_type == 2:  # R_ARM_ABS32
                addend = r_addend if is_rela else struct.unpack_from("<i", t_buf, r_offset)[0]
                val = (S + addend) & 0xFFFFFFFF
                struct.pack_into("<I", t_buf, r_offset, val)
                if relocs_out is not None and not sym["external"] and sym["shndx"] != 0xFFF1:   # SHN_ABS stays
                    relocs_out.append(P - base_addr)
            elif r_type == 10 and relocs_out is not None and sym["external"]:
                raise ValueError(f"heap code: direct call to {sym['name']} outside the image (call it through a pointer)")
            elif r_type == 10:  # R_ARM_THM_CALL
                # Metrowerks RELA uses r_addend = -4 for Thumb BL
                bl_bytes = encode_thumb_bl(P, S)
                t_buf[r_offset : r_offset + 4] = bl_bytes
            else:
                raise ValueError(f"Unsupported relocation type {r_type} at {target_sec['name']}+0x{r_offset:X}")

    # Assemble flat binary image
    image = bytearray(total_size)
    for s in sections:
        if "vaddr" in s and s["type"] != 8:  # Copy non-NOBITS sections
            rel_off = s["vaddr"] - base_addr
            image[rel_off : rel_off + s["size"]] = s["content"]

    return bytes(image), sym_addrs, sections


def module_info():
    """{module: (vanilla path, extracted path, base address)} for arm9 and every overlay."""
    mods = {"arm9": (VANILLA_EXTRACTED / "arm9" / "arm9.bin", EXTRACTED_DIR / "arm9" / "arm9.bin", ARM9_BASE_ADDR)}
    y = (VANILLA_EXTRACTED / "arm9_overlays" / "overlays.yaml").read_text()
    for blk in y.split("- id:")[1:]:
        n = int(blk.split()[0])
        base = int(re.search(r"base_address:\s*(\d+)", blk).group(1))
        name = f"ov{n:03d}"
        mods[name] = (VANILLA_EXTRACTED / "arm9_overlays" / f"{name}.bin",
                      EXTRACTED_DIR / "arm9_overlays" / f"{name}.bin", base)
    return mods


def apply_patches(syms):
    from patches import PATCHES
    mods = module_info()
    data = {}
    skip = [x for x in os.environ.get("ACWW_SKIP", "").split(",") if x]   # experiments: skip patches by value
    for mod, addr, kind, expect, value, note in PATCHES:
        if "*" in skip or any(x in str(value) for x in skip):
            print(f"      SKIP  {mod} 0x{addr:08X} {value}")
            continue
        if mod not in data:
            data[mod] = bytearray(mods[mod][0].read_bytes())
        buf, base = data[mod], mods[mod][2]
        off = addr - base
        exp = bytes.fromhex(expect)
        if buf[off: off + len(exp)] != exp:
            raise RuntimeError(f"{mod} 0x{addr:08X}: expected {expect}, found {buf[off:off+len(exp)].hex()} ({note})")
        if kind == "bl":
            if value not in syms:
                raise RuntimeError(f"missing payload symbol {value}")
            new = encode_thumb_bl(addr, syms[value])
        elif kind == "ptr":
            new = struct.pack("<I", syms[value] | 1)
        elif kind == "dptr":
            new = struct.pack("<I", syms[value])
        elif kind == "bytes":
            new = bytes.fromhex(value)
        else:
            raise ValueError(kind)
        buf[off: off + len(new)] = new
        print(f"      {mod:5s} 0x{addr:08X} {kind:5s} {value:30s} {note}")
    # Every module starts from vanilla on each build; patched ones are then overwritten
    for mod, (src, dst, _) in mods.items():
        if mod in data:
            dst.write_bytes(data[mod])
        elif not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)


def apply_file_patches():
    """Restores the files edited by the previous build, then applies tools/file_patches.py on fresh copies."""
    from file_patches import FILE_PATCHES
    src = VANILLA_EXTRACTED / "files"
    dst = EXTRACTED_DIR / "files"
    log = ROOT_DIR / "build" / "files_modified.txt"
    if log.exists():
        for rel in log.read_text().split():
            shutil.copyfile(src / rel, dst / rel)
    done = []
    for fn in FILE_PATCHES:
        for rel in fn(src, dst):
            done.append(str(rel).replace(chr(92), "/"))
            print(f"      files/{done[-1]}  ({fn.__name__})")
    log.write_text(chr(10).join(done) + chr(10))


def write_unity_source():
    """All src/*.c compiled as one translation unit (one ELF for the tiny linker)."""
    files = sorted(p for p in (ROOT_DIR / "src").glob("*.c"))
    UNITY_C.write_text("".join(f'#include "{p.as_posix()}"' + chr(10) for p in files))
    return files


HEAP_UNITY_C = ROOT_DIR / "build" / "acww_heap_unity.c"
HEAP_OBJ_O = ROOT_DIR / "build" / "acww_heap.o"
HEAP_FILE_REL = Path("zplus") / "code.bin"
# Export order = the HX_* slots in src/code_home.h
HX_EXPORTS = ["hx_claim_vram", "hx_can_place", "hx_load_model"]


def build_heap_code(itcm_syms):
    """src/heap/*.c -> files/zplus/code.bin (see src/code_home.c for the format)."""
    files = sorted(p for p in (ROOT_DIR / "src" / "heap").glob("*.c"))
    HEAP_UNITY_C.write_text("".join(f'#include "{p.as_posix()}"' + chr(10) for p in files))
    compile_c_source(HEAP_UNITY_C, HEAP_OBJ_O)
    relocs = []
    image, syms, _ = link_elf_object(HEAP_OBJ_O, 0, externs=itcm_syms, relocs_out=relocs)
    exports = [syms[n] | 1 for n in HX_EXPORTS]
    relocs = sorted(set(relocs))
    hdr = struct.pack("<4I", 0x50485741, len(image), len(exports), len(relocs))
    blob = hdr + struct.pack(f"<{len(exports)}I", *exports) + struct.pack(f"<{len(relocs)}I", *relocs) + image
    out = EXTRACTED_DIR / "files" / HEAP_FILE_REL
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(blob)
    # dsd places only files listed in path_order.txt (an unlisted file gets an empty FAT entry): list it last
    order = (VANILLA_EXTRACTED / "path_order.txt").read_text().splitlines()
    order.append("/" + HEAP_FILE_REL.as_posix())
    (EXTRACTED_DIR / "path_order.txt").write_text(chr(10).join(order) + chr(10))
    (ROOT_DIR / "build" / "heap.map").write_text(chr(10).join(
        f"0x{a:08X} {n}" for n, a in sorted(syms.items(), key=lambda kv: kv[1]) if n and not n.startswith(("@", "."))
        and a < len(image)) + chr(10))
    print(f"      Heap code: {len(image)} bytes, {len(relocs)} relocations -> files/{HEAP_FILE_REL.as_posix()} "
          f"({len(blob)} bytes)")


def main():
    files = write_unity_source()
    print(f"      Sources: {', '.join(p.name for p in files)}")
    compile_c_source()

    print(f"[2/4] Linking {OBJ_O.name} at ITCM 0x{PAYLOAD_BASE_ADDR:08X}...")
    payload, syms, sections = link_elf_object(OBJ_O, PAYLOAD_BASE_ADDR)
    PAYLOAD_BIN.write_bytes(payload)
    map_lines = [f"0x{a:08X} {n}" for n, a in sorted(syms.items(), key=lambda kv: kv[1])
                 if n and not n.startswith(("@", "."))]
    (ROOT_DIR / "build" / "payload.map").write_text(chr(10).join(map_lines) + chr(10))

    end_addr = PAYLOAD_BASE_ADDR + len(payload)
    print(f"      Payload size: {len(payload)} bytes (0x{PAYLOAD_BASE_ADDR:08X} .. 0x{end_addr:08X}), "
          f"{ITCM_END_ADDR - end_addr} bytes of ITCM left")
    if end_addr > ITCM_END_ADDR:
        raise RuntimeError(f"Payload overflows ITCM end 0x{ITCM_END_ADDR:08X}!")

    print("[3/4] Patching binaries (fresh vanilla copies + tools/patches.py)...")
    vanilla_itcm = (VANILLA_EXTRACTED / "arm9" / "itcm.bin").read_bytes()
    if len(vanilla_itcm) > PAYLOAD_OFFSET_IN_ITCM:
        raise RuntimeError("Vanilla itcm.bin is larger than expected payload offset 0x5C00")
    padded_itcm = bytearray(vanilla_itcm) + bytearray(PAYLOAD_OFFSET_IN_ITCM - len(vanilla_itcm)) + bytearray(payload)
    if os.environ.get("ACWW_NO_PAYLOAD") == "1":   # experiments: vanilla ITCM image
        padded_itcm = bytearray(vanilla_itcm)
    (EXTRACTED_DIR / "arm9" / "itcm.bin").write_bytes(padded_itcm)
    itcm_yaml_txt = (VANILLA_EXTRACTED / "arm9" / "itcm.yaml").read_text(encoding="utf-8")
    itcm_yaml_txt = re.sub(r"code_size:\s*\d+", f"code_size: {len(padded_itcm)}", itcm_yaml_txt)
    (EXTRACTED_DIR / "arm9" / "itcm.yaml").write_text(itcm_yaml_txt, encoding="utf-8")
    # Keep vanilla's compression flags: an earlier build had arm9 + all overlays "compressed: false", which
    # cost ~12% of the ARM9 in town (tools/probes/headroom_probe.py: idle 47% vs 59%).
    shutil.copyfile(VANILLA_EXTRACTED / "arm9" / "arm9.yaml", EXTRACTED_DIR / "arm9" / "arm9.yaml")
    shutil.copyfile(VANILLA_EXTRACTED / "arm9_overlays" / "overlays.yaml", EXTRACTED_DIR / "arm9_overlays" / "overlays.yaml")
    apply_patches(syms)
    if os.environ.get("ACWW_NO_FILES") != "1":
        apply_file_patches()
    build_heap_code(syms)

    print(f"[4/4] Building ROM {OUT_ROM}...")
    build_cmd = [
        str(DSD_EXE),
        "rom", "build",
        "--config", str(EXTRACTED_DIR / "config.yaml"),
        "--rom", str(OUT_ROM),
    ]
    res = subprocess.run(build_cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)
    print(f"Done! Built {OUT_ROM} ({OUT_ROM.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
