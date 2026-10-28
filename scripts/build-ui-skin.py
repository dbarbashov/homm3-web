"""Render an optional browser skin from the user's original game resources.

The generated CSS embeds PNGs and stays outside Git, like fonts.css.
Requires Pillow and a configured local asset server.
"""
import argparse
import base64
import io
import struct
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def fetch(server, name):
    with urllib.request.urlopen(server.rstrip('/') + '/api/asset?name=' + name, timeout=30) as response:
        return response.read()


def bitmap(data, player_palette=None):
    if len(data) < 12:
        raise ValueError('Truncated game bitmap')
    size, width, height = struct.unpack_from('<III', data)
    if not (0 < width <= 4096 and 0 < height <= 4096):
        raise ValueError('Invalid game bitmap dimensions')
    if size == width * height and len(data) >= 12 + size + 768:
        image = Image.frombytes('P', (width, height), data[12:12 + size])
        palette = bytearray(data[12 + size:12 + size + 768])
        if player_palette is not None:
            palette[224 * 3:] = player_palette
        image.putpalette(palette)
        return image.convert('RGB')
    if size == width * height * 3 and len(data) >= 12 + size:
        return Image.frombytes('RGB', (width, height), data[12:12 + size], 'raw', 'BGR')
    raise ValueError('Unsupported or truncated game bitmap')


def menu_sprites(data, player_palette):
    """Render system-options button states from the original IAM009 DEF."""
    kind, width, height, groups = struct.unpack_from('<4I', data)
    if (width, height, groups) != (32, 32, 1):
        raise ValueError('Unexpected system-options sprite')
    palette = bytearray(data[16:784])
    palette[224 * 3:] = player_palette
    count = struct.unpack_from('<I', data, 788)[0]
    frames = []
    for index in range(2):
        offset = struct.unpack_from('<I', data, 800 + count * 13 + index * 4)[0]
        size, fmt, full_w, full_h, w, h, left, top = struct.unpack_from('<8I', data, offset)
        if fmt != 1 or (w, h, left, top) != (32, 32, 0, 0):
            raise ValueError('Unexpected system-options frame encoding')
        payload = offset + 32
        pixels = bytearray()
        for row in range(h):
            cursor = payload + struct.unpack_from('<I', data, payload + row * 4)[0]
            line = bytearray()
            while len(line) < w:
                code, length = data[cursor:cursor + 2]
                cursor += 2
                length += 1
                if code == 255:
                    line.extend(data[cursor:cursor + length])
                    cursor += length
                else:
                    line.extend(bytes([code]) * length)
            if len(line) != w:
                raise ValueError('Invalid system-options sprite row')
            pixels.extend(line)
        image = Image.frombytes('P', (w, h), bytes(pixels))
        image.putpalette(palette)
        frames.append(image.convert('RGB'))
    return frames


def frame(image, inset=16):
    """Keep original corners and repeating edges; omit the dialog contents."""
    result = Image.new('RGBA', (inset * 3, inset * 3))
    for row, y in enumerate((0, image.height // 2 - inset // 2, image.height - inset)):
        for col, x in enumerate((0, image.width // 2 - inset // 2, image.width - inset)):
            if row != 1 or col != 1:
                result.paste(image.crop((x, y, x + inset, y + inset)), (col * inset, row * inset))
    return result


def blank_button(image):
    """Retain the gold bevel; tile its text-free metal underneath HTML labels."""
    result = image.copy()
    strip = image.crop((5, 5, image.width - 5, 8))
    for y in range(5, image.height - 5, strip.height):
        height = min(strip.height, image.height - 5 - y)
        result.paste(strip.crop((0, 0, strip.width, height)), (5, y))
    return result


def data_url(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return 'url("data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode() + '")'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', default='http://127.0.0.1:8783')
    args = parser.parse_args()
    palette = fetch(args.server, 'players.pal')
    # RIFF PAL: 24-byte header, 256 RGBA records. Player zero is red.
    if len(palette) < 1048 or palette[:4] != b'RIFF' or palette[8:16] != b'PAL data':
        raise ValueError('Invalid Players.pal')
    red = bytes(value for index in range(32) for value in palette[24 + index * 4:27 + index * 4])
    dialog = bitmap(fetch(args.server, 'sysopbck.pcx'), red)
    if dialog.size != (481, 487):
        raise ValueError('Unexpected system-options layout')
    images = {
        'leather': bitmap(fetch(args.server, 'dibox128.pcx')),
        'frame': frame(dialog),
        'gold-button': blank_button(dialog.crop((246, 298, 346, 346))),
        'dark-button': dialog.crop((28, 77, 74, 109)),
    }
    normal, pressed = menu_sprites(fetch(args.server, 'iam009.def'), red)
    images.update({'menu-icon': normal, 'menu-icon-pressed': pressed})
    output = ROOT / 'web/site/skin.css'
    output.write_text('/* Locally rendered original game assets. Do not commit. */\n:root{\n' +
                      '\n'.join('--h3-' + name + ':' + data_url(image) + ';' for name, image in images.items()) + '\n}\n')
    print(f'Rendered {len(images)} skin elements: {output} ({output.stat().st_size} bytes, excluded from Git)')


if __name__ == '__main__':
    main()
