#!/usr/bin/env python3
"""
Builds the AC:WW+ Outdoor Furniture ROM hack (e:/acww-plus/build/acww_plus.nds).

Steps:
1. Compiles src/outdoor_furniture.c -> build/outdoor_furniture.o using Metrowerks mwccarm.exe.
2. Parses the ELF32 relocatable object, places .text, .rodata, .data, and .bss at 0x01FFDC00
   (offset 0x5C00 in ITCM, inside the 9,504-byte unused tail 0x01FFDAE0..0x02000000).
3. Resolves all R_ARM_ABS32 and R_ARM_THM_CALL relocations.
4. Copies clean vanilla binaries (arm9.bin, itcm.bin, ov003.bin) from E:/claudeGameDecomp/extracted,
   appends the linked ITCM payload, updates itcm.yaml code_size, and patches the 4 Thumb BL hooks:
   - Hook 1 (ov003 @ 0x022212C2): BL hook_ov003_draw_item + B 0x022212FA
   - Hook 2 (ov003 @ 0x02220ADA): BL hook_ov003_teardown
   - Hook 3 (ov003 @ 0x02223586): BL hook_ov003_item_shape_lookup
   - Hook 4 (arm9  @ 0x02042DB4): BL hook_outdoor_drop_item
5. Invokes dsd-windows-x86_64.exe rom build to produce build/acww_plus.nds.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(r"e:\acww-plus")
SRC_C = ROOT_DIR / "src" / "outdoor_furniture.c"
OBJ_O = ROOT_DIR / "build" / "outdoor_furniture.o"
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


def compile_c_source():
    cmd = [
        str(MWCCARM_EXE),
        "-O4,s",
        "-inline", "off",
        "-proc", "arm946e",
        "-thumb",
        "-interworking",
        "-c", str(SRC_C),
        "-o", str(OBJ_O),
    ]
    env = os.environ.copy()
    env["MWCIncludes"] = "."
    env["LM_LICENSE_FILE"] = str(MWCCARM_EXE.parents[2] / "license.dat")
    print(f"[1/4] Compiling {SRC_C.name} with mwccarm.exe...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)


def link_elf_object(obj_path: Path, base_addr: int):
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
            raise ValueError(f"Undefined external symbol in object: {name}")
        symbols.append({"name": name, "vaddr": vaddr, "info": st_info, "shndx": st_shndx, "size": st_size})
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


def main():
    compile_c_source()

    print(f"[2/4] Linking {OBJ_O.name} at ITCM 0x{PAYLOAD_BASE_ADDR:08X}...")
    payload, syms, sections = link_elf_object(OBJ_O, PAYLOAD_BASE_ADDR)
    PAYLOAD_BIN.write_bytes(payload)
    map_lines = [f"0x{a:08X} {n}" for n, a in sorted(syms.items(), key=lambda kv: kv[1])
                 if n and not n.startswith(("@", "."))]
    (ROOT_DIR / "build" / "payload.map").write_text("\n".join(map_lines) + "\n")

    end_addr = PAYLOAD_BASE_ADDR + len(payload)
    print(f"      Payload size: {len(payload)} bytes (0x{PAYLOAD_BASE_ADDR:08X} .. 0x{end_addr:08X})")
    if end_addr > ITCM_END_ADDR:
        raise RuntimeError(f"Payload overflows ITCM end 0x{ITCM_END_ADDR:08X}!")

    required_hooks = [
        "hook_ov003_draw_item",
        "hook_ov003_teardown",
        "hook_ov003_item_shape",
        "hook_outdoor_drop_item",
        "hook_field_put_spot_check",
    ]
    for h in required_hooks:
        if h not in syms:
            raise RuntimeError(f"Missing required hook symbol: {h}")
        print(f"      Symbol {h:30s} @ 0x{syms[h]:08X}")

    print("[3/4] Patching extracted binaries (itcm.bin, itcm.yaml, ov003.bin, arm9.bin)...")

    # 3a. Patch itcm.bin and itcm.yaml
    vanilla_itcm = (VANILLA_EXTRACTED / "arm9" / "itcm.bin").read_bytes()
    if len(vanilla_itcm) > PAYLOAD_OFFSET_IN_ITCM:
        raise RuntimeError("Vanilla itcm.bin is larger than expected payload offset 0x5C00")
    padded_itcm = bytearray(vanilla_itcm) + bytearray(PAYLOAD_OFFSET_IN_ITCM - len(vanilla_itcm)) + bytearray(payload)
    (EXTRACTED_DIR / "arm9" / "itcm.bin").write_bytes(padded_itcm)

    itcm_yaml_path = EXTRACTED_DIR / "arm9" / "itcm.yaml"
    itcm_yaml_txt = (VANILLA_EXTRACTED / "arm9" / "itcm.yaml").read_text(encoding="utf-8")
    itcm_yaml_txt = re.sub(r"code_size:\s*\d+", f"code_size: {len(padded_itcm)}", itcm_yaml_txt)
    itcm_yaml_path.write_text(itcm_yaml_txt, encoding="utf-8")

    # 3b. Patch ov003.bin
    ov003_data = bytearray((VANILLA_EXTRACTED / "arm9_overlays" / "ov003.bin").read_bytes())

    # Hook 1: ov003 @ 0x022212C0 (adds r0, r7, #0 at +0, BL hook_ov003_draw_item at +2, B 0x022212FA at +6)
    h1_addr = 0x022212C0
    h1_off = h1_addr - OV003_BASE_ADDR
    assert ov003_data[h1_off : h1_off + 2] == bytes.fromhex("381c"), "Unexpected bytes at Hook 1"
    ov003_data[h1_off + 2 : h1_off + 6] = encode_thumb_bl(h1_addr + 2, syms["hook_ov003_draw_item"])
    ov003_data[h1_off + 6 : h1_off + 8] = bytes.fromhex("18e0")  # b #0x022212fa

    # Hook 2: ov003 @ 0x02220ADA (replace BL 0x020454D4 with BL hook_ov003_teardown)
    h2_addr = 0x02220ADA
    h2_off = h2_addr - OV003_BASE_ADDR
    assert ov003_data[h2_off : h2_off + 4] == bytes.fromhex("24f6fbfc"), "Unexpected bytes at Hook 2"
    ov003_data[h2_off : h2_off + 4] = encode_thumb_bl(h2_addr, syms["hook_ov003_teardown"])

    # Hook 3: ov003 data @ 0x022366E4: function pointer ov003_item_shape -> hook_ov003_item_shape
    h3_addr = 0x022366E4
    h3_off = h3_addr - OV003_BASE_ADDR
    assert struct.unpack_from("<I", ov003_data, h3_off)[0] == 0x02223559, "Unexpected pointer at Hook 3"
    struct.pack_into("<I", ov003_data, h3_off, syms["hook_ov003_item_shape"] | 1)

    (EXTRACTED_DIR / "arm9_overlays" / "ov003.bin").write_bytes(ov003_data)

    # 3c. Patch arm9.bin
    arm9_data = bytearray((VANILLA_EXTRACTED / "arm9" / "arm9.bin").read_bytes())

    # Hook 4: arm9 @ 0x02042DB4 (replace BL 0x02042DC4 with BL hook_outdoor_drop_item)
    h4_addr = 0x02042DB4
    h4_off = h4_addr - ARM9_BASE_ADDR
    assert arm9_data[h4_off : h4_off + 4] == bytes.fromhex("00f006f8"), "Unexpected bytes at Hook 4"
    arm9_data[h4_off : h4_off + 4] = encode_thumb_bl(h4_addr, syms["hook_outdoor_drop_item"])

    # Hook 5: arm9 @ 0x02042B7A (field_put_spot_find: BL field_put_spot_check -> hook_field_put_spot_check)
    h5_addr = 0x02042B7A
    h5_off = h5_addr - ARM9_BASE_ADDR
    assert arm9_data[h5_off : h5_off + 4] == bytes.fromhex("00f04bf8"), "Unexpected bytes at Hook 5"
    arm9_data[h5_off : h5_off + 4] = encode_thumb_bl(h5_addr, syms["hook_field_put_spot_check"])

    (EXTRACTED_DIR / "arm9" / "arm9.bin").write_bytes(arm9_data)

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
