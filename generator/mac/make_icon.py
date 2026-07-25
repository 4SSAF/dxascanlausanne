#!/usr/bin/env python3
"""Génère AppIcon.icns (icône de l'app Mac). Nécessite Pillow.
    pip install pillow && python make_icon.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

S = 1024
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",          # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
]


def font(sz):
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def rounded(size, rad):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=rad, fill=255)
    return m


def build():
    top, bot = (18, 124, 150), (9, 66, 84)   # dégradé teal de marque
    grad = Image.new("RGB", (S, S), bot)
    g = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        g.line([(0, y), (S, y)], fill=tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    mask = rounded(S, int(S * 0.225))
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(grad.convert("RGBA"), (0, 0), mask)

    # sheen supérieur
    sheen = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).rounded_rectangle([0, 0, S - 1, int(S * 0.5)],
                                            radius=int(S * 0.225), fill=(255, 255, 255, 26))
    icon = Image.alpha_composite(icon, Image.composite(sheen, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask))

    dr = ImageDraw.Draw(icon)
    fM = font(int(S * 0.56))
    b = dr.textbbox((0, 0), "M", font=fM)
    dr.text(((S - (b[2] - b[0])) / 2 - b[0], (S - (b[3] - b[1])) / 2 - b[1] - int(S * 0.06)),
            "M", font=fM, fill=(255, 255, 255, 255))
    dr.rounded_rectangle([int(S * 0.30), int(S * 0.70), int(S * 0.70), int(S * 0.735)],
                         radius=int(S * 0.02), fill=(255, 255, 255, 235))
    fc = font(int(S * 0.085))
    cb = dr.textbbox((0, 0), "DXA", font=fc)
    dr.text(((S - (cb[2] - cb[0])) / 2 - cb[0], int(S * 0.76)), "DXA", font=fc, fill=(255, 255, 255, 210))

    out = os.path.join(HERE, "AppIcon.icns")
    icon.save(out)
    print("écrit :", out)


if __name__ == "__main__":
    build()
