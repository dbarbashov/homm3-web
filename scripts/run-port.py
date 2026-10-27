"""Launch the native C++ client with the configured local game installation."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
game=Path(json.loads((ROOT/'.local/game.json').read_text())['gameRoot'])
raise SystemExit(subprocess.call([str(ROOT/'build/homm3-port'),str(game/'Data')+'/',*sys.argv[1:]],cwd=ROOT))
