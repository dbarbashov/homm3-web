"""Build an allowlisted, deployment archive from explicitly selected web files; run from repository root."""
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
files = ['favicon.ico', 'index.html', 'viewer.html', 'app.js', 'engine.js', 'renderer.js', 'style.css', 'engine.wasm']
files += ['site/' + name for name in ['favicon.png', 'site.css', 'mobile.css', 'mobile.js', 'touch.js', 'report-bug.js', 'game.webmanifest', 'assets.js', 'video-archive.js', 'rooms.js', 'credits.html', 'resources.json']]
files += ['port/' + name for name in ['game.html', 'game.js', 'game.wasm', 'boot.js', 'sha256.js', 'music.js', 'sfx.js']]
output = root / '.local/deploy'
output.mkdir(parents=True, exist_ok=True)
with tarfile.open(output / 'site.tar.gz', 'w:gz') as tar:
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
    tar.add(root / '.local/ffmpeg-8.0.3.tar.xz', arcname='web/sources/ffmpeg-8.0.3.tar.xz')
    tar.add(root / 'licenses/ffmpeg-LGPL-2.1.txt', arcname='web/sources/ffmpeg-LGPL-2.1.txt')
    # Local development reports include screenshots and machine paths: keep them off the VPS.
    status = output / 'public-status.html'
    status.write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Тест Heroes III Web</title><link rel="stylesheet" href="/site/site.css"><main class="landing"><h1>Закрытый тест</h1><p>До 50 комнат. Чат: 300 символов, раз в 2 секунды, до 10 сообщений в минуту.</p><p>Для игры выберите папку собственной установки. Возврат в начатую партию после разрыва связи пока недоступен.</p><p><a href="/port/game.html">К игре</a> · <a href="/site/credits.html">Авторы и лицензии</a></p></main></html>')
    tar.add(status, arcname='web/site/status.html')
print(output / 'site.tar.gz')
