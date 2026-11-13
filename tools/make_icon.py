"""Draw the app icon (Save Card style: red/green slash on asphalt, chequered strip) -> assets/icon.ico + icon.png.

Run: python tools/make_icon.py   (needs Pillow; only for changing the icon, not for building)
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'dm_save_update', 'assets')
S = 1024  # drawn large, scaled down for smooth edges


def draw():
    img = Image.new('RGBA', (S, S), '#15120F')
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, S - 1, S - 1], outline='#3A322A', width=24)
    # chequered strip at the bottom
    sq = S // 8
    top = S - sq - 40
    half = sq // 2
    for i in range(8):  # two rows, white squares alternate
        y = top if i % 2 == 0 else top + half
        d.rectangle([i * sq, y, i * sq + sq - 1, y + half - 1], fill='#F4EDE2')
    # the slash: two skewed bars, red and green
    h0, h1 = 120, top - 70
    w, lean, gap = 190, 230, 60
    x = (S - (2 * w + gap + lean)) // 2 + lean
    for colour in ('#E2372B', '#3DC36B'):
        d.polygon([(x, h0), (x + w, h0), (x + w - lean, h1), (x - lean, h1)], fill=colour)
        x += w + gap
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    img = draw()
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, 'icon.png'))
    img.save(os.path.join(OUT, 'icon.ico'), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                                                   (256, 256)])
    print('written to', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
