"""Record current staged edits as a reviewable patch against the pinned source."""
from pathlib import Path
import difflib
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'upstream/homm3-decomp'
staged=ROOT/'build/portable-source'
chunks=[]
for folder in ['include','src']:
    for old in sorted((source/folder).rglob('*')):
        if not old.is_file():continue
        rel=old.relative_to(source);new=staged/rel
        if new.exists() and old.read_bytes()!=new.read_bytes():
            chunks.extend(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile=f'a/{rel}',tofile=f'b/{rel}'))
dest=ROOT/'port/patches/0001-portability.patch';dest.parent.mkdir(exist_ok=True)
dest.write_text(''.join(chunks))
print(f'{len(chunks)} patch lines written')
