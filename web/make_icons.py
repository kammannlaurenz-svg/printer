"""Erzeugt die PWA-Icons (App-Symbol: Bon aus einem Drucker)."""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
os.makedirs(OUT, exist_ok=True)

S = 512  # Basisgroesse


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render(size=S, maskable=False):
    img = Image.new("RGB", (size, size), (79, 70, 229))
    d = ImageDraw.Draw(img)

    # Diagonaler Farbverlauf (Indigo -> Violett)
    c1, c2 = (79, 70, 229), (139, 92, 246)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(c1, c2, y / size))

    # Glyph mittig; bei maskable etwas kleiner (Safe-Zone)
    scale = 0.52 if maskable else 0.62
    g = int(size * scale)
    ox = (size - g) // 2
    oy = (size - g) // 2
    white = (255, 255, 255)

    # Druckerkorpus
    body_top = oy + int(g * 0.42)
    body = [ox + int(g * 0.06), body_top, ox + int(g * 0.94), oy + int(g * 0.82)]
    d.rounded_rectangle(body, radius=int(g * 0.10), fill=white)

    # kleiner "Power"-Punkt am Drucker (Akzentfarbe)
    r = int(g * 0.035)
    cx, cy = ox + int(g * 0.80), body_top + int(g * 0.12)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(79, 70, 229))

    # Bon, der oben herauskommt
    px0, px1 = ox + int(g * 0.20), ox + int(g * 0.80)
    py0, py1 = oy + int(g * 0.04), body_top + int(g * 0.10)
    d.rectangle([px0, py0, px1, py1], fill=white)

    # Zackenrand unten am Bon
    teeth = 7
    tw = (px1 - px0) / teeth
    th = int(g * 0.05)
    for i in range(teeth):
        x = px0 + i * tw
        d.polygon([(x, py1), (x + tw / 2, py1 + th), (x + tw, py1)], fill=white)

    # Textzeilen auf dem Bon (Akzentfarbe)
    line_c = (99, 102, 241)
    for i, w in enumerate([0.9, 0.7, 0.85, 0.55]):
        ly = py0 + int(g * 0.10) + i * int(g * 0.075)
        lx1 = px0 + int(g * 0.08)
        lx2 = px0 + int((px1 - px0) * w) - int(g * 0.02)
        d.rounded_rectangle([lx1, ly, lx2, ly + int(g * 0.028)], radius=int(g * 0.014), fill=line_c)

    return img


def main():
    base = render(S, maskable=False)
    base.resize((192, 192), Image.LANCZOS).save(os.path.join(OUT, "icon-192.png"))
    base.save(os.path.join(OUT, "icon-512.png"))
    base.resize((180, 180), Image.LANCZOS).save(os.path.join(OUT, "apple-touch-icon.png"))
    render(S, maskable=True).save(os.path.join(OUT, "icon-maskable-512.png"))
    print("Icons erstellt in:", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  ", f)


if __name__ == "__main__":
    main()
