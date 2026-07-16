"""Generate Cushion component icons: orange squishy-blob style,
transparent background, 24x24 (drawn 16x supersampled).

Run: python3 make_icons.py   ->  <name>.png (24px) + preview.png sheet
"""

import math
import os

from PIL import Image, ImageDraw

S = 384          # supersample canvas
OUT = 24
ORANGE = (240, 84, 35, 255)
DARK = (45, 45, 45, 255)
WHITE = (255, 255, 255, 255)
GRAY = (200, 200, 200, 255)
LW = 18          # outline width at supersample scale

HERE = os.path.dirname(os.path.abspath(__file__))


def blob(d, box, fill=ORANGE, outline=DARK):
    d.ellipse(box, fill=fill, outline=outline, width=LW)


def canvas():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(img, name):
    img = img.resize((OUT, OUT), Image.LANCZOS)
    img.save(os.path.join(HERE, name + ".png"))
    return img


BODY_BOX = (30, 110, 354, 300)   # default blob


def icon_body():
    img, d = canvas()
    blob(d, BODY_BOX)
    return img


def icon_cavity():
    img, d = canvas()
    blob(d, BODY_BOX)
    d.ellipse((130, 165, 254, 245), fill=(0, 0, 0, 0), outline=DARK, width=LW)
    return img


def _cable(d, y, x0=60, x1=324, n=4):
    d.line([(x0, y), (x1, y)], fill=DARK, width=LW)
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        r = 22
        d.ellipse((x - r, y - r, x + r, y + r), fill=DARK)


def icon_tendon():
    img, d = canvas()
    blob(d, BODY_BOX)
    _cable(d, 205)
    return img


def icon_tendons():
    img, d = canvas()
    blob(d, BODY_BOX)
    for y in (160, 205, 250):
        _cable(d, y, n=3)
    return img


def icon_region():
    img, d = canvas()
    blob(d, BODY_BOX)
    d.ellipse((150, 150, 320, 260), fill=(200, 60, 20, 255), outline=DARK,
              width=LW)
    return img


def icon_target():
    img, d = canvas()
    blob(d, (30, 190, 354, 330))
    # cube resting on the cushion
    d.polygon([(140, 90), (250, 90), (250, 200), (140, 200)], fill=GRAY,
              outline=DARK)
    d.line([(140, 90), (250, 90)], fill=DARK, width=LW)
    return img


def icon_profile():
    img, d = canvas()
    d.line([(60, 40), (60, 330), (350, 330)], fill=DARK, width=LW)
    pts = [(60, 300), (170, 140), (270, 140), (340, 60)]
    d.line(pts, fill=ORANGE, width=LW + 8)
    for x, y in pts[1:]:
        r = 24
        d.ellipse((x - r, y - r, x + r, y + r), fill=WHITE, outline=DARK,
                  width=12)
    return img


def icon_profiles():
    img, d = canvas()
    for k, y0 in enumerate((70, 190, 310)):
        d.line([(50, y0 + 30), (350, y0 + 30)], fill=DARK, width=10)
        d.line([(50, y0 + 30), (170, y0 - 30), (350, y0 - 10)],
               fill=ORANGE, width=LW + 4)
    return img


def icon_scene():
    img, d = canvas()
    # folder
    d.polygon([(40, 110), (150, 110), (180, 145), (350, 145), (350, 330),
               (40, 330)], fill=WHITE, outline=DARK)
    d.line([(40, 110), (150, 110), (180, 145), (350, 145), (350, 330),
            (40, 330), (40, 110)], fill=DARK, width=LW)
    blob(d, (85, 200, 305, 305))
    return img


def icon_run():
    img, d = canvas()
    blob(d, BODY_BOX)
    d.polygon([(150, 140), (150, 270), (270, 205)], fill=WHITE, outline=DARK)
    return img


def icon_preview():
    img, d = canvas()
    blob(d, (30, 200, 354, 340))
    # eye
    d.ellipse((90, 60, 300, 210), fill=WHITE, outline=DARK, width=LW)
    d.ellipse((160, 100, 230, 170), fill=DARK)
    return img


def icon_results():
    img, d = canvas()
    blob(d, (30, 190, 250, 340))
    # trajectory dots arcing away, clearly separated
    for t in (0.15, 0.45, 0.75, 1.0):
        x = 170 + 190 * t
        y = 210 - 190 * t + 70 * t * t
        r = 26
        d.ellipse((x - r, y - r, x + r, y + r), fill=DARK)
    return img


def icon_shape():
    img, d = canvas()
    # ghost (rest shape), dashed
    steps = 40
    cx, cy, rx, ry = 250, 160, 120, 80
    for i in range(0, steps, 2):
        a0 = 2 * math.pi * i / steps
        a1 = 2 * math.pi * (i + 1) / steps
        d.line([(cx + rx * math.cos(a0), cy + ry * math.sin(a0)),
                (cx + rx * math.cos(a1), cy + ry * math.sin(a1))],
               fill=(120, 120, 120, 255), width=12)
    # deformed blob, rotated ellipse
    tilt = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(tilt)
    blob(td, (60, 150, 300, 300))
    tilt = tilt.rotate(25, center=(180, 225), resample=Image.BICUBIC)
    img.alpha_composite(tilt)
    return img


ICONS = {
    "SofaBody": icon_body,
    "SofaCavity": icon_cavity,
    "SofaTendon": icon_tendon,
    "SofaTendons": icon_tendons,
    "SofaRegion": icon_region,
    "SofaTarget": icon_target,
    "PressureProfile": icon_profile,
    "SofaProfiles": icon_profiles,
    "SofaScene": icon_scene,
    "SofaRun": icon_run,
    "SofaPreview": icon_preview,
    "SofaResults": icon_results,
    "SofaShape": icon_shape,
}


def main():
    small = {}
    for name, fn in ICONS.items():
        small[name] = save(fn(), name)
        print("wrote", name + ".png")

    # preview sheet at 4x for human QA
    cols = 5
    rows = (len(small) + cols - 1) // cols
    cell = OUT * 4 + 8
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 255, 255, 255))
    for i, (name, im) in enumerate(small.items()):
        big = im.resize((OUT * 4, OUT * 4), Image.NEAREST)
        sheet.alpha_composite(big, ((i % cols) * cell + 4, (i // cols) * cell + 4))
    sheet.save(os.path.join(HERE, "preview.png"))
    print("wrote preview.png")


if __name__ == "__main__":
    main()
