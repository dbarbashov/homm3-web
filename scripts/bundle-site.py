"""Build an allowlisted, deployment archive from explicitly selected web files; run from repository root."""
from pathlib import Path
import tarfile
import subprocess
import sys
import argparse
import hashlib
import os

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ffmpeg-source', type=Path,
                    default=Path(os.environ.get('HOMM3_FFMPEG_SOURCE', root / '.local/ffmpeg-8.0.3.tar.xz')))
args = parser.parse_args()
if not args.ffmpeg_source.is_file():
    parser.error('Supply the FFmpeg 8.0.3 source archive with --ffmpeg-source or HOMM3_FFMPEG_SOURCE')
if hashlib.sha256(args.ffmpeg_source.read_bytes()).hexdigest() != '6136812ea6d4e68bdba27e33c2a94382711cdf4f8602ffef056ff792bd6f9818':
    parser.error('FFmpeg source checksum mismatch')
subprocess.run([sys.executable, str(root / 'scripts/engine-client.py'), 'verify'], check=True)
files = ['favicon.ico', 'index.html']
files += ['site/' + name for name in ['crest.webp', 'ui-leather.webp', 'ui-gold.webp', 'favicon.png', 'site.css', 'mobile.css', 'mobile.js', 'touch.js', 'report-bug.js', 'telemetry.js', 'privacy.html', 'game.webmanifest', 'assets.js', 'video-archive.js', 'rooms.js', 'fast-game.js', 'authority-game.js', 'credits.html', 'resources.json']]
files += ['port/' + name for name in ['game.html', 'game.js', 'game.wasm', 'engine-build.json', 'boot.js', 'sha256.js', 'music.js', 'sfx.js']]
output = root / '.local/deploy'
output.mkdir(parents=True, exist_ok=True)
with tarfile.open(output / 'site.tar.gz', 'w:gz', dereference=True) as tar:
    for name in files:
        path = root / 'web' / name
        if not path.is_file():
            raise FileNotFoundError(path)
        tar.add(path, arcname='web/' + name)
    for name in ['fonts.css', 'skin.css']:
        generated = root / 'web/site' / name
        if not generated.is_file():
            generated = output / name
            generated.write_text('/* Optional locally generated UI assets. */\n')
        tar.add(generated, arcname='web/site/' + name)
    tar.add(args.ffmpeg_source, arcname='web/sources/ffmpeg-8.0.3.tar.xz')
    tar.add(root / 'licenses/ffmpeg-LGPL-2.1.txt', arcname='web/sources/ffmpeg-LGPL-2.1.txt')
    # Local development reports include screenshots and machine paths: keep them off the VPS.
    status = output / 'public-status.html'
    status.write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Тест Heroes III Web</title><link rel="stylesheet" href="/site/site.css"><main class="landing"><h1>Heroes III в браузере · 0.3.0</h1><p>До 50 комнат. Чат: 300 символов, раз в 2 секунды, до 10 сообщений в минуту.</p><p>Для игры выберите папку собственной установки. Обычные сетевые партии сохраняются автоматически и доступны в разделе «Мои партии» в том же браузере. Быстрая игра — экспериментальный режим.</p><p><a href="/port/game.html">К игре</a> · <a href="/site/credits.html">Авторы и лицензии</a></p></main></html>')
    tar.add(status, arcname='web/site/status.html')
print(output / 'site.tar.gz')
