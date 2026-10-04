"""Regenere les icones web et Android a partir de frontend/branding/logo-source.png.

Usage (depuis la racine du depot) :
    docker compose run --rm web python frontend/scripts/make-icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'branding' / 'logo-source.png'
PUBLIC = ROOT / 'public'
RES = ROOT / 'android' / 'app' / 'src' / 'main' / 'res'


def white_to_alpha(img):
    """Rend le fond blanc transparent (doux), en gardant couleurs et degrades du logo."""
    img = img.convert('RGBA')
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, _ = px[x, y]
            distance = 255 - min(r, g, b)
            alpha = max(0, min(255, int((distance - 6) * 5)))
            px[x, y] = (r, g, b, alpha)
    return img


def crop_to_content(img, margin=0.04):
    bbox = img.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
    img = img.crop(bbox)
    pad = int(max(img.size) * margin)
    canvas = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad))
    return canvas


def fit(img, size, ratio=1.0, background=None):
    """Centre le logo dans un carre `size`, occupant `ratio` de la largeur."""
    target = int(size * ratio)
    scale = target / max(img.size)
    resized = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), background or (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
    return canvas


def circle(img):
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, img.width - 1, img.height - 1), fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out


def main():
    logo = crop_to_content(white_to_alpha(Image.open(SRC)))

    PUBLIC.mkdir(exist_ok=True)
    fit(logo, 512, 0.92).save(PUBLIC / 'logo.png', optimize=True)
    fit(logo, 192, 0.92).save(PUBLIC / 'icon-192.png', optimize=True)
    fit(logo, 512, 0.80, (255, 255, 255, 255)).save(PUBLIC / 'icon-512.png', optimize=True)
    fit(logo, 180, 0.74, (255, 255, 255, 255)).convert('RGB').save(PUBLIC / 'apple-touch-icon.png', optimize=True)
    fit(logo, 64, 0.94).save(PUBLIC / 'favicon.png', optimize=True)

    legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    adaptive = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}
    for density, size in legacy.items():
        folder = RES / f'mipmap-{density}'
        square = fit(logo, size, 0.74, (255, 255, 255, 255))
        square.save(folder / 'ic_launcher.png', optimize=True)
        circle(square).save(folder / 'ic_launcher_round.png', optimize=True)
    for density, size in adaptive.items():
        # Zone sure des icones adaptatifs : ~66 % du carre de 108 dp
        fit(logo, size, 0.60).save(RES / f'mipmap-{density}' / 'ic_launcher_foreground.png', optimize=True)

    # Ecran de demarrage : logo sur fond blanc (memes noms que les ressources Capacitor)
    for folder in RES.glob('drawable*'):
        splash = folder / 'splash.png'
        if splash.exists():
            width, height = Image.open(splash).size
            canvas = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            icon = fit(logo, min(width, height), 0.34)
            canvas.alpha_composite(icon, ((width - icon.width) // 2, (height - icon.height) // 2))
            canvas.convert('RGB').save(splash, optimize=True)
    print('Icones generees')


if __name__ == '__main__':
    main()
