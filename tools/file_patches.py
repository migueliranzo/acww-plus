"""
NitroFS file edits for AC:WW+ (applied by tools/build_rom.py on fresh vanilla copies).

New text is English in every language (owner decision 2026-10-19: English first, other languages fall back
to the English text until translated).
"""
from pathlib import Path

import bmg_tool

LANGS = ["ENG", "FRN", "GER", "ITA", "SPN"]


def look_menu_text(src: Path, dst: Path):
    """Features 3 + 4: 'Change my look.' in the upstairs phone's Service Center (src/skin_tone.c)."""
    out = []
    for lang in LANGS:
        rel = Path("script") / lang / "select" / "select2.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert b.msgs[22][0] == b"", f"{rel}: select2 #22 is not empty"
        b.msgs[22][0] = bmg_tool.encode("Change my look.")
        b.save(dst / rel)
        out.append(rel)

        rel = Path("script") / lang / "message" / "sp" / "etc" / "sequence1_.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert len(b.msgs) == 0x43, f"{rel}: expected 0x43 messages, found {len(b.msgs)}"
        ask_attr = b.msgs[17][1]                      # a question with inline choices ("how should they talk")

        def reply_to(nxt):                            # a reply that continues to message nxt
            a = bytearray(b.msgs[16][1])
            a[4] = nxt
            return bytes(a)

        new = [
            # 0x43 look menu: 4 choices -> skin question, shoes, socks, "anything else?"
            ("What would you like to\nchange?{2:2:4447481f}\nSkin tone.\nShoes.\nSocks.\nThat's all.", ask_attr),
            # 0x44 skin question: Lighter / Darker -> 0x45 / 0x46, This is fine -> look menu
            ("What kind of skin tone\nwould you like?{2:1:454643}\nLighter.\nDarker.\nThis is fine.", ask_attr),
            # 0x45 / 0x46 skin replies -> back to the skin question
            ("There we go!{1:0:0500}\nHow does that look?", reply_to(0x44)),
            ("There we go!{1:0:0500}\nHow does that look?", reply_to(0x44)),
            # 0x47 / 0x48 shoe / sock replies -> back to the look menu
            ("How about these shoes?", reply_to(0x43)),
            ("How about these socks?", reply_to(0x43)),
        ]
        for text, attr in new:
            b.msgs.append([bmg_tool.encode(text), attr])
        b.save(dst / rel)
        out.append(rel)
    return out


FRUIT_FIRST = 0x518            # item_info index of the apple (item 0x1518); orange, pear, peach, cherry follow
FRUIT_STACK_FIRST = 0x56E      # first blank record: 5 fruits x counts 2..9 = 40 records, 0x56E..0x595
FRUIT_STACK_MAX = 9
FRUIT_PLURALS = {
    "ENG": ["apples", "oranges", "pears", "peaches", "cherries"],
    "FRN": ["pommes", "oranges", "poires", "pêches", "cerises"],
    "GER": ["Äpfel", "Orangen", "Birnen", "Pfirsiche", "Kirschen"],
    "ITA": ["mele", "arance", "pere", "pesche", "ciliegie"],
    "SPN": ["manzanas", "naranjas", "peras", "melocotones", "cerezas"],
}
FRUIT_STACK_ATTR = {"FRN": b"\xff\xff\x00", "GER": b"\xff\xff\x01"}   # as the turnip stacks; others ff ff ff


def fruit_stack_items(src: Path, dst: Path):
    """Fruit stacks (src/heap/fruit_stack.c): records 0x56E..0x595 = '2 apples' .. '9 cherries'.
    Each copies its fruit's record (icon, kind), with the price times the count; the names are plurals."""
    out = []
    for lang in LANGS:
        names = FRUIT_PLURALS.get(lang, FRUIT_PLURALS["ENG"])
        for fname, size in (("always.bin", 12), ("indoor.bin", 4), ("dma.bin", 20)):
            rel = Path("item_info") / lang / fname
            name_at = 3                           # dma.bin: EU records have 3 attribute bytes, then the name
            if not (src / rel).exists():          # the US games (English only): no language folders, 2 attribute
                rel = Path("item_info") / fname   # bytes (the EU's first two), the name at +2
                name_at = 2
            b = bytearray((src / rel).read_bytes())
            assert len(b) == 0x600 * size, f"{rel}: unexpected size {len(b)}"
            for k in range(5):
                fruit = b[(FRUIT_FIRST + k) * size:(FRUIT_FIRST + k + 1) * size]
                for n in range(2, FRUIT_STACK_MAX + 1):
                    i = FRUIT_STACK_FIRST + k * 8 + n - 2
                    assert not any(b[i * size:(i + 1) * size]), f"{rel}: record 0x{i:X} is not blank"
                    rec = bytearray(fruit)
                    if fname == "always.bin":
                        rec[0:2] = (int.from_bytes(fruit[0:2], "little") * n).to_bytes(2, "little")
                    elif fname == "dma.bin":
                        name = f"{n} {names[k]}".encode("latin-1")
                        assert len(name) < size - name_at, name
                        rec[0:name_at] = FRUIT_STACK_ATTR.get(lang, b"\xff\xff\xff")[:name_at]
                        rec[name_at:] = name.ljust(size - name_at, b"\0")
                    b[i * size:(i + 1) * size] = rec
            (dst / rel).write_bytes(b)
            out.append(rel)
    return out


FILE_PATCHES = [look_menu_text, fruit_stack_items]
