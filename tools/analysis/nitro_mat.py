"""List materials of a BMD0 (inside an .arc NARC or raw): flags, origW/H, texImageParam.
usage: py -3.12 -I nitro_mat.py FILE"""
import struct, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import nitro_tex as N


def find_bmd(d):
    i = d.find(b"BMD0")
    return d[i:] if i >= 0 else None


def materials(bmd):
    mdl0 = None
    nblk = struct.unpack_from("<H", bmd, 0xE)[0]
    for i in range(nblk):
        o = struct.unpack_from("<I", bmd, 0x10 + 4 * i)[0]
        if bmd[o:o + 4] == b"MDL0":
            mdl0 = o
    models = N.dict_names(bmd, mdl0 + 8)
    out = []
    for mname, ent in models:
        model = mdl0 + struct.unpack_from("<I", bmd, ent)[0]
        ofs_mat = struct.unpack_from("<I", bmd, model + 8)[0]
        resmat = model + ofs_mat
        mats = N.dict_names(bmd, resmat + 4)
        for name, e in mats:
            md = resmat + struct.unpack_from("<I", bmd, e)[0]
            tag, size, diffamb, specemi, pattr, pmask, tip, tipmask, pbase, flag, ow, oh = struct.unpack_from("<HHIIIIIIHHHH", bmd, md)
            out.append(dict(model=mname, mat=name, flag=flag, origW=ow, origH=oh, texImageParam=tip, texgen=(tip >> 30) & 3))
    return out


if __name__ == "__main__":
    d = N.lz10(open(sys.argv[1], "rb").read())
    for m in materials(find_bmd(d)):
        print(m["mat"], f"flag={m['flag']:#06x}", "orig", m["origW"], m["origH"], f"texgen={m['texgen']}", f"tip={m['texImageParam']:#010x}")
