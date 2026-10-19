"""Print decompiled function(s) by name or address from the read-only reference decomps.
usage: py -3.12 tools/analysis/fn.py NAME_OR_ADDR [...]"""
import re, sys, glob
R = r"C:\NDS_RECOMP\prototype\runs"
FILES = sorted(glob.glob(R + r"\2026-10-16-naming\wave*\R*\region_lit.c")) + [
    R + r"\2026-10-16-night\N4\work\ov003.c", R + r"\2026-10-16-night\N3\work\ov004.c"] + \
    sorted(glob.glob(R + r"\2026-10-16-night\N5\work\HP\res\ov*.c")) + sorted(glob.glob(R + r"\2026-10-16-night\N5\dec\ov*.c")) + \
    [R + r"\2026-10-16-night\N5\dec2\ov002.c"]
HDR = re.compile(r"^// ={4,5} (\S+) @ (\S+)")
def main():
    for q in sys.argv[1:]:
        ql = q.lower().replace("0x", "")
        found = False
        for f in FILES:
            try: lines = open(f, encoding="utf-8", errors="replace").read().split("\n")
            except FileNotFoundError: continue
            for i, l in enumerate(lines):
                m = HDR.match(l)
                if m and (m.group(1) == q or ql in m.group(2).lower().replace("0x", "")) :
                    j = i + 1
                    while j < len(lines) and not HDR.match(lines[j]): j += 1
                    print(f"/* {f} */"); print("\n".join(lines[i:j]).rstrip()); found = True
                    break
            if found: break
        if not found: print("// not found:", q)
main()
