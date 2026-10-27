"""Run the C++ client with private writable directories and read-only retail assets."""
from pathlib import Path
import json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
game=Path(json.loads((ROOT/'.local/game.json').read_text())['gameRoot'])
runtime=ROOT/'.local/runtime';runtime.mkdir(parents=True,exist_ok=True)
data=runtime/'data'
if data.is_symlink():data.unlink()
data.mkdir(exist_ok=True)
for source in (game/'Data').iterdir():
    if source.suffix.lower() in ('.lod','.snd','.vid') and not (data/source.name).exists():
        (data/source.name).symlink_to(source)
for target, source in [('maps','Maps'),('mp3','Mp3')]:
    link=runtime/target
    if not link.exists():link.symlink_to(game/source,target_is_directory=True)
for name in ['games','random_maps']:(runtime/name).mkdir(exist_ok=True)
raise SystemExit(subprocess.call([os.environ.get('HOMM3_NATIVE_BINARY',str(ROOT/'build/homm3-game')),str(runtime),*sys.argv[1:]],cwd=ROOT))
