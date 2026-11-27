#!/usr/bin/env python3
"""Compose README / demo-page images of the plugin face from the same pre-rendered assets the
plugin draws (Decorator/resources/img/ui_*@2x.png), with the knobs at chosen positions."""
import os, math
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "Decorator", "resources", "img"); OUT = os.path.join(HERE, "..", "docs", "img")
S = 2  # assets are 2x
def frames(name, n):
    im = Image.open(os.path.join(IMG, name)).convert("RGBA"); cols = math.ceil(math.sqrt(n))
    fw, fh = im.width // cols, im.height // math.ceil(n / cols)
    return [im.crop(((i % cols) * fw, (i // cols) * fh, (i % cols + 1) * fw, (i // cols + 1) * fh)) for i in range(n)]
BG = Image.open(os.path.join(IMG, "ui_bg@2x.png")).convert("RGBA")
KB, KS, LED = frames("ui_knob_big@2x.png", 81), frames("ui_knob_small@2x.png", 81), frames("ui_led@2x.png", 2)
CB, CS = Image.open(os.path.join(IMG, "ui_cap_big@2x.png")).convert("RGBA"), Image.open(os.path.join(IMG, "ui_cap_small@2x.png")).convert("RGBA")
def paste(dst, im, cx, cy): dst.alpha_composite(im, (int(round(cx * S - im.width / 2)), int(round(cy * S - im.height / 2))))
def face(sat_h, vol_h, on=True):
    im = BG.copy(); cx, top = 150, 16
    v = lambda h: (h - 7) / 10
    paste(im, KB[round(v(sat_h) * 80)], cx, top + 129); paste(im, CB, cx, top + 129)
    paste(im, KS[round(v(vol_h) * 80)], cx, top + 287); paste(im, CS, cx, top + 287)
    paste(im, LED[0 if on else 1], cx, top + 488)
    im = im.crop((21 * S, 17 * S, 279 * S, 725 * S))
    from PIL import ImageDraw
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=14 * S, fill=255)
    im.putalpha(m); return im
os.makedirs(OUT, exist_ok=True)
hero = face(14.0, 12.0); hero.save(os.path.join(OUT, "decorator.png"), optimize=True)
hero.resize((hero.width // 2, hero.height // 2), Image.LANCZOS).save(os.path.join(OUT, "decorator-small.png"), optimize=True)
# row of the demo settings
row = [face(h, 12.0, on) for h, on in ((9, False), (9, True), (12, True), (15, True), (17, True))]
w, h = row[0].width // 2, row[0].height // 2; gap = 24
strip = Image.new("RGBA", (len(row) * w + (len(row) - 1) * gap, h), (0, 0, 0, 0))
for i, r in enumerate(row): strip.alpha_composite(r.resize((w, h), Image.LANCZOS), (i * (w + gap), 0))
strip.save(os.path.join(OUT, "settings.png"), optimize=True)
for i, (h_, on) in enumerate(((9, False), (9, True), (12, True), (15, True), (17, True))):
    face(h_, 12.0, on).resize((w // 2, h // 2), Image.LANCZOS).save(os.path.join(OUT, f"thumb_{i}.png"), optimize=True)
print("ok", hero.size, strip.size)
