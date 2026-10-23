import sys, os, glob; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import bmg_tool
files = glob.glob(r'E:\claudeGameDecomp\extracted\files\script\*\select\*.bmg') + glob.glob(r'E:\claudeGameDecomp\extracted\files\script\*\message\sp\etc\*.bmg')
tmp = os.path.join(os.environ['TEMP'], 'bmg_rt.bmg'); ok=0; bad=[]
for f in files:
    b = bmg_tool.Bmg(f); b.save(tmp)
    if bmg_tool.unwrap(open(tmp,'rb').read()) == bmg_tool.unwrap(open(f,'rb').read()): ok += 1
    else: bad.append(f)
print('identical', ok, 'of', len(files), bad[:3])
