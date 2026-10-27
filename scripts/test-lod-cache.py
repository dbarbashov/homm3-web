"""Check the bounded archive cache against independent compressed fixtures."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['clang++','-std=c++14','-O2','-Iport/compat','port/probes/lod_cache.cpp','port/platform/lod_cache.cpp','-lz','-o','build/lod-cache-probe'],cwd=ROOT,check=True)
subprocess.run([str(ROOT/'build/lod-cache-probe')],cwd=ROOT,check=True)
