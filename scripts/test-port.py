"""Cross-target resource rendering parity and native front-end lifecycle."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'test-results';out.mkdir(exist_ok=True)
game=Path(json.loads((ROOT/'.local/game.json').read_text())['gameRoot'])
results=[]
for target,command in [('native',[str(ROOT/'build/resource-probe')]),('web',['node',str(ROOT/'build/resource-probe.cjs')])]:
    subprocess.run([sys.executable,'scripts/link-probe.py','--target',target],cwd=ROOT,check=True)
    run=subprocess.run(command+[str(game/'Data')+'/'],cwd=ROOT,capture_output=True,text=True,timeout=60,check=True)
    results.append(json.loads(run.stdout))
assert results[0]==results[1], 'Native/WASM resource pixels differ'
(out/'cpp-resource-parity.json').write_text(json.dumps({'nativeEqualsWasm':True,**results[0]},indent=2))
snapshots=[]
for screen, hover_ids in [('main', [-1,101,102,103,104,105]), ('new', [-1,100,101,102,103,104]), ('load', [-1])]:
    for hover in hover_ids:
        args=[str(ROOT/'build/homm3-port'),str(game/'Data')+'/','--snapshot',screen]
        if hover!=-1:args.append(str(hover))
        run=subprocess.run(args,cwd=ROOT,env={**os.environ,'SDL_VIDEODRIVER':'dummy','SDL_RENDER_DRIVER':'software'},
            capture_output=True,text=True,check=True,timeout=15)
        snapshot=json.loads(run.stdout)
        snapshots.append({**snapshot,'hover':hover})
        if screen=='main' and hover==-1:
            (out/'cpp-native.json').write_text(json.dumps(snapshot,indent=2))
(out/'frontend-native.json').write_text(json.dumps(snapshots,indent=2))
print(f'Native exits cleanly for {len(snapshots)} menu states. Pixel parity: {len(results[0]["checks"])} assets / {sum(x["frames"] for x in results[0]["checks"])} frames.')
