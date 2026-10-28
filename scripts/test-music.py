"""Compare actual native music PCM against the original envelope and resume rules."""

from pathlib import Path
import subprocess, shlex

ROOT = Path(__file__).resolve().parents[1]
flags = shlex.split(
    subprocess.check_output(["sdl2-config", "--cflags", "--libs"], text=True)
)
subprocess.run(
    [
        "clang++",
        "-std=c++14",
        "port/probes/music.cpp",
        "port/platform/music.cpp",
        *flags,
        "-o",
        "build/music-probe",
    ],
    cwd=ROOT,
    check=True,
)
run = subprocess.run(
    [str(ROOT / "build/music-probe"), str(ROOT / ".local/runtime")],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=30,
)
print(run.stdout, run.stderr)
(ROOT / "test-results/music-native.json").write_text(run.stdout)
raise SystemExit(run.returncode)
