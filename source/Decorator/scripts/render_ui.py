#!/usr/bin/env python3
"""Offline renderer for the Decorator UI: lit, textured bitmaps instead of flat vector drawing.

Outputs (resources/img, 2x scale = 2 px per UI point):
  ui_bg@2x.png           600x1560  enclosure, legends, logo, LED bezel, footswitch, shadows
  ui_knob_big@2x.png     filmstrip, N frames of the Saturation knob (vertical)
  ui_knob_small@2x.png   filmstrip, N frames of the Volume knob
  ui_led@2x.png          2 frames: lit, unlit lens
All lighting is fixed in screen space, so knob highlights stay put while the knob turns.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "resources")
S = 2  # px per point
W, H = 300 * S, 780 * S
PEDAL = (20 * S, 16 * S, 280 * S, 726 * S)  # l, t, r, b
KNOB_FRAMES = 81
rng = np.random.default_rng(7)

# ---------- shading helpers ----------
LIGHT_POS = np.array([-0.15 * W, -0.25 * H, 0.9 * H])  # soft key light above, top-left
FILL = np.array([0.3, 0.2, 1.0]) / np.linalg.norm([0.3, 0.2, 1.0])
V = np.array([0.0, 0.0, 1.0])


def normals_from_height(h, strength=1.0):
    gy, gx = np.gradient(h * strength)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def light_dirs(shape, ox=0.0, oy=0.0):
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(float)
    L = np.dstack([LIGHT_POS[0] - (xx + ox), LIGHT_POS[1] - (yy + oy), np.full(shape, LIGHT_POS[2])])
    return L / np.linalg.norm(L, axis=2, keepdims=True)


def env_color(r):
    """Studio environment for chrome/aluminium reflections: bright softboxes above, dark floor."""
    x, y, z = r[..., 0], r[..., 1], r[..., 2]
    up = np.clip(-y * 0.8 + z * 0.4, -1, 1)
    base = 0.42 + 0.5 * np.clip(up, 0, 1) ** 1.2 + 0.12 * np.clip(z, 0, 1)
    box1 = np.exp(-(((x + 0.35) / 0.25) ** 2 + ((y + 0.55) / 0.18) ** 2)) * 0.9
    box2 = np.exp(-(((x - 0.45) / 0.3) ** 2 + ((y + 0.2) / 0.35) ** 2)) * 0.45
    floor = np.clip(y, 0, 1) * 0.12
    return np.clip(base + box1 + box2 - floor, 0, 1.3)


def reflect(n, v=V):
    d = np.sum(n * v, axis=2, keepdims=True)
    return 2 * d * n - v


def kajiya_kay(T, L, p):
    Hh = L + V
    Hh = Hh / np.linalg.norm(Hh, axis=2, keepdims=True)
    th = np.sum(T * Hh, axis=2)
    return np.clip(1 - th ** 2, 0, 1) ** (p / 2)


def rounded_rect_dist(shape, l, t, r, b, rad):
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(float)
    cx, cy = (l + r) / 2, (t + b) / 2
    hx, hy = (r - l) / 2 - rad, (b - t) / 2 - rad
    qx, qy = np.abs(xx - cx) - hx, np.abs(yy - cy) - hy
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rad
    return -outside  # positive inside, = distance to edge


def to_img(rgb, alpha=None):
    rgb8 = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alpha is None:
        return Image.fromarray(rgb8, "RGB")
    a8 = (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb8, a8]), "RGBA")


def over(dst_rgb, src_rgb, src_a):
    a = src_a[..., None]
    return dst_rgb * (1 - a) + src_rgb * a


# ---------- enclosure ----------
def render_background():
    l, t, r, b = PEDAL
    shape = (H, W)
    d = rounded_rect_dist(shape, l, t, r, b, 16 * S)
    inside = np.clip(d + 0.5, 0, 1)  # anti-aliased mask
    yy, xx = np.mgrid[0:H, 0:W].astype(float)

    # height: rounded side edges, plus folds where the sheet bends down at top and bottom
    bevel = 7.0 * S
    edge = np.clip(d / bevel, 0, 1)
    h = np.sqrt(1 - (1 - edge) ** 2) * bevel * 0.9
    fold = 24.0 * S
    ft = np.clip((yy - t) / fold, 0, 1)
    fb = np.clip((b - yy) / fold, 0, 1)
    h += (np.sin(ft * np.pi / 2) - 1) * fold * 0.55 + (np.sin(fb * np.pi / 2) - 1) * fold * 0.55

    # brushed grain: noise smeared along x, plus faint mottling like the real finish
    n = rng.standard_normal(shape)
    brushed = ndimage.gaussian_filter(n, sigma=(0.45, 70.0))
    brushed /= brushed.std()
    mottle = ndimage.gaussian_filter(rng.standard_normal(shape), 3.5) + 0.6 * ndimage.gaussian_filter(rng.standard_normal(shape), 12.0)
    mottle /= mottle.std()
    fine = ndimage.gaussian_filter(rng.standard_normal(shape), 0.7)
    fine /= fine.std()

    N = normals_from_height(h + brushed * 0.12 + mottle * 0.10)
    L = light_dirs(shape)
    ndl = np.clip(np.sum(N * L, axis=2), 0, 1)
    fill = np.clip(np.sum(N * FILL, axis=2), 0, 1)
    T = np.dstack([np.ones(shape), np.zeros(shape), np.zeros(shape)])  # brush direction
    spec = kajiya_kay(T, L, 60) * (0.85 + 0.15 * brushed)
    env = env_color(reflect(N))

    albedo = np.array([0.835, 0.805, 0.765]) * (1 + 0.016 * brushed + 0.022 * mottle + 0.018 * fine)[..., None]
    # broad satin sheen: lighter toward the upper left, like the photo
    sheen = np.exp(-(((xx - (l + 0.3 * (r - l))) / (0.55 * (r - l))) ** 2 + ((yy - (t + 0.3 * (b - t))) / (0.6 * (b - t))) ** 2))
    lum = 0.30 + 0.38 * ndl + 0.12 * fill + 0.10 * sheen
    rgb = albedo * lum[..., None] + 0.10 * spec[..., None] + 0.07 * env[..., None] * np.array([1.0, 0.98, 0.95])
    # gentle edge darkening (occlusion near the bends)
    occl = 1 - 0.10 * (1 - np.clip(d / (30 * S), 0, 1))
    rgb *= occl[..., None]

    # backdrop with a soft cast shadow of the enclosure
    bg = np.ones((H, W, 3)) * np.array([0.085, 0.085, 0.09])
    sh = ndimage.gaussian_filter(np.clip(rounded_rect_dist(shape, l + 4, t + 14, r + 4, b + 14, 16 * S) + 0.5, 0, 1), 12)
    bg *= (1 - 0.6 * sh)[..., None]
    out = over(bg, rgb, inside)
    return out, inside


def print_legends(rgb, inside):
    """Printed black legends (Montserrat Bold) and the DECORATOR logo, with slight print texture."""
    l, t, r, b = PEDAL
    mask = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(mask)
    bold = os.path.join(RES, "fonts", "Montserrat-Bold.ttf")
    reg = os.path.join(RES, "fonts", "Roboto-Regular.ttf")

    def centred(text, font, y):
        w = dr.textlength(text, font=font)
        dr.text(((l + r) / 2 - w / 2, y), text, fill=255, font=font)

    f_label = ImageFont.truetype(bold, 15 * S)
    centred("SATURATION", f_label, t + 206 * S)
    centred("VOLUME", f_label, t + 350 * S)
    centred("BYPASS", ImageFont.truetype(bold, 13 * S), t + 514 * S)
    f_sub = ImageFont.truetype(reg, 15 * S)
    centred("– tape saturation", f_sub, t + 430 * S)
    ink = np.asarray(mask).astype(float) / 255.0

    logo = Image.open(os.path.join(RES, "img", "DecoratorLogo@3x.png")).convert("RGBA")
    lw = 220 * S
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    la = np.zeros((H, W))
    x0, y0 = int((l + r) / 2 - lw / 2), int(t + 410 * S - logo.height / 2)
    la[y0 : y0 + logo.height, x0 : x0 + lw] = np.asarray(logo)[..., 3] / 255.0
    ink = np.maximum(ink, la)
    ink *= 0.93 + 0.07 * ndimage.gaussian_filter(rng.standard_normal(ink.shape), 0.8)  # print texture
    ink = np.clip(ink, 0, 1) * inside
    paint = np.array([0.11, 0.105, 0.1])
    return over(rgb, paint, ink * 0.96)


def chrome_shade(N):
    env = env_color(reflect(N))
    return np.clip(env * 0.85 + 0.08, 0, 1)[..., None] * np.array([1.0, 0.99, 0.98])


def draw_led_bezel_and_footswitch(rgb):
    l, t, r, b = PEDAL
    cx = (l + r) / 2
    yy, xx = np.mgrid[0:H, 0:W].astype(float)

    # LED bezel: chrome ring around a dark socket
    ly = t + 488 * S
    rr = np.hypot(xx - cx, yy - ly)
    ring_out, ring_in = 15 * S, 10.5 * S
    ring = np.clip(ring_out - rr + 0.5, 0, 1) * np.clip(rr - ring_in + 0.5, 0, 1)
    hring = np.sqrt(np.clip(1 - ((rr - (ring_out + ring_in) / 2) / ((ring_out - ring_in) / 2)) ** 2, 0, 1)) * 6
    Nring = normals_from_height(hring)
    shadow = ndimage.gaussian_filter(np.clip(ring_out + 2 - np.hypot(xx - cx - 2, yy - ly - 4), 0, 1), 4)
    rgb = rgb * (1 - 0.35 * shadow * (1 - ring))[..., None]
    rgb = over(rgb, chrome_shade(Nring) * 0.9, ring)
    socket = np.clip(ring_in - rr + 0.5, 0, 1)
    rgb = over(rgb, np.array([0.05, 0.045, 0.045]), socket)

    # footswitch: chrome hex nut and a domed chrome button
    fy = t + 597 * S
    ang = np.arctan2(yy - fy, xx - cx)
    rr = np.hypot(xx - cx, yy - fy)
    R = 48 * S
    k = np.pi / 3
    hexr = R * np.cos(np.pi / 6) / np.cos(((ang - np.pi / 6) % k) - k / 2)  # hexagon radius per angle
    nut = np.clip(hexr - rr + 0.5, 0, 1)
    hn = np.clip((hexr - rr) / (6 * S), 0, 1) ** 0.5 * 8 + np.clip(R * 0.82 - rr, 0, 1) * 0
    sh = ndimage.gaussian_filter(np.clip(hexr - np.hypot(xx - cx - 3, yy - fy - 9) + 0.5, 0, 1), 10)
    rgb = rgb * (1 - 0.5 * sh * (1 - nut))[..., None]
    rgb = over(rgb, chrome_shade(normals_from_height(hn)) * 0.95, nut)
    # threaded collar ring
    collar = np.clip(R * 0.80 - rr + 0.5, 0, 1) * np.clip(rr - R * 0.70 + 0.5, 0, 1)
    hc = np.sqrt(np.clip(1 - ((rr - R * 0.75) / (R * 0.05)) ** 2, 0, 1)) * 5
    rgb = over(rgb, chrome_shade(normals_from_height(hc)) * 0.85, collar)
    # domed button
    rb_ = R * 0.66
    btn = np.clip(rb_ - rr + 0.5, 0, 1)
    hb = np.sqrt(np.clip(1 - (rr / rb_) ** 2, 0, 1)) * rb_ * 0.35
    Nb = normals_from_height(hb + ndimage.gaussian_filter(rng.standard_normal(hb.shape), 2.0) * 0.015)
    bshade = chrome_shade(Nb) * 0.92 + 0.04
    gap = ndimage.gaussian_filter(np.clip(rb_ + 2 * S - rr, 0, 1) * (1 - btn), 1.5)
    rgb = rgb * (1 - 0.5 * gap)[..., None]
    rgb = over(rgb, bshade, btn)
    return rgb


# ---------- knobs ----------
def render_knob_frames(radius_pt, frames=KNOB_FRAMES, px_center=None):
    R = radius_pt * S
    M = int(R * 1.28)  # frame half-size incl. shadow margin
    size = 2 * M
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    dx, dy = xx - M, yy - M
    rr = np.hypot(dx, dy)
    th = np.arctan2(dx, -dy)  # 0 at 12 o'clock, clockwise
    ox, oy = (px_center[0] - M, px_center[1] - M) if px_center else (W / 2 - M, H / 2 - M)
    L = light_dirs((size, size), ox, oy)
    # cap (does not depend on rotation)
    rc = R * 0.62
    cap = np.clip(rc - rr + 0.5, 0, 1)
    hcap = 14 + np.sqrt(np.clip(1 - (np.clip(rr - rc + 2.5 * S, 0, None) / (2.5 * S)) ** 2, 0, 1)) * 3
    spun = ndimage.gaussian_filter(rng.standard_normal((size, size)), 0.6)
    Ncap = normals_from_height(hcap)
    Tcap = np.dstack([np.cos(th), np.sin(th), np.zeros_like(th)])  # circumferential (image coords)
    Tcap = np.dstack([-dy, dx, np.zeros_like(dx)]) / np.maximum(rr, 1)[..., None]
    spec_cap = kajiya_kay(Tcap, L, 30)
    cap_rgb = (0.42 + 0.35 * np.clip(np.sum(Ncap * L, axis=2), 0, 1))[..., None] * np.array([0.86, 0.86, 0.85])
    cap_rgb = cap_rgb + 0.42 * spec_cap[..., None] + 0.04 * spun[..., None]
    cap_rgb = 0.85 * cap_rgb + 0.15 * chrome_shade(Ncap)

    strips = []
    for f in range(frames):
        a = np.deg2rad(-150 + 300 * f / (frames - 1))
        rs = R * (0.955 + 0.045 * np.cos(9 * (th - a)))
        skirt = np.clip(rs - rr + 0.5, 0, 1)
        # skirt height: rounded rim, flat top, step up to a raised inner ring
        hs = np.sqrt(np.clip((rs - rr) / (6 * S), 0, 1)) * 10 + np.clip((R * 0.80 - rr) / (1.5 * S), 0, 1) * 3
        Ns = normals_from_height(hs)  # no per-frame noise: it would shimmer while turning and bloat the filmstrip
        ndl = np.clip(np.sum(Ns * L, axis=2), 0, 1)
        Hh = L + V
        Hh /= np.linalg.norm(Hh, axis=2, keepdims=True)
        blinn = np.clip(np.sum(Ns * Hh, axis=2), 0, 1) ** 45
        plastic = (0.035 + 0.06 * ndl)[..., None] * np.ones(3) + 0.30 * blinn[..., None] + 0.05 * env_color(reflect(Ns))[..., None]
        rgb = plastic
        # white pointer line painted on the skirt
        px, py = np.sin(a), -np.cos(a)
        along = dx * px + dy * py
        across = np.abs(dx * py - dy * px)
        ptr = np.clip(1.6 * S - across, 0, 1) * (along > R * 0.80) * (along < R * 0.985) * skirt
        rgb = over(rgb, np.array([0.93, 0.93, 0.9]) * (0.75 + 0.25 * ndl)[..., None], ptr)
        # soft cast shadow (fixed light offset), under the skirt
        sil = skirt
        shadow = ndimage.shift(ndimage.gaussian_filter(sil, 6 * S / 2), (5 * S, 2 * S), order=1)
        alpha = np.clip(skirt + shadow * 0.55 * (1 - skirt), 0, 1)
        col = np.where(skirt[..., None] > 0, rgb, 0.0)
        # premultiply-style composite of shadow colour
        out_rgb = np.where((skirt > 0)[..., None], rgb, np.zeros(3))
        strips.append((out_rgb, alpha, skirt))
    cap_img = to_img(np.clip(cap_rgb, 0, 1), cap)
    return strips, size, cap_img


def strip_image(frames):
    """Frames in a near-square grid (row-major): a tall strip would exceed GPU texture limits."""
    imgs = [to_img(np.clip(rgb, 0, 1), alpha) for rgb, alpha, _ in frames]
    w, h = imgs[0].size
    cols = int(np.ceil(np.sqrt(len(imgs))))
    rows = int(np.ceil(len(imgs) / cols))
    sheet = Image.new("RGBA", (w * cols, h * rows))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    return sheet


def render_led():
    size = 76 * S
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    c = size / 2
    rr = np.hypot(xx - c, yy - c)
    lens_r = 9.5 * S
    lens = np.clip(lens_r - rr + 0.5, 0, 1)
    hl = np.sqrt(np.clip(1 - (rr / lens_r) ** 2, 0, 1)) * lens_r * 0.6
    N = normals_from_height(hl)
    L = light_dirs((size, size), PEDAL[0] + 130 * S - c, PEDAL[1] + 488 * S - c)
    Hh = L + V
    Hh /= np.linalg.norm(Hh, axis=2, keepdims=True)
    spec = np.clip(np.sum(N * Hh, axis=2), 0, 1) ** 80
    frames = []
    for lit in (True, False):
        if lit:
            core = np.exp(-((rr / (lens_r * 0.55)) ** 2))
            body = np.array([0.95, 0.12, 0.08]) * (0.55 + 0.45 * core)[..., None] + np.array([1, 0.75, 0.6]) * (core ** 3)[..., None] * 0.6
            glow = np.exp(-((rr / (lens_r * 2.6)) ** 2)) * 0.55 * (1 - lens)
            rgb = over(np.array([1.0, 0.18, 0.1]) * np.ones((size, size, 3)), body, lens)
            alpha = np.clip(lens + glow, 0, 1)
        else:
            body = np.array([0.30, 0.05, 0.05]) * (0.6 + 0.4 * np.clip(np.sum(N * L, axis=2), 0, 1))[..., None]
            rgb, alpha = body, lens
        rgb = rgb + 0.5 * spec[..., None] * lens[..., None]
        frames.append((np.clip(rgb, 0, 1), alpha, lens))
    return frames


def main():
    out = os.path.join(RES, "img")
    rgb, inside = render_background()
    rgb = print_legends(rgb, inside)
    rgb = draw_led_bezel_and_footswitch(rgb)
    to_img(rgb).save(os.path.join(out, "ui_bg@2x.png"), optimize=True)
    l, t, r, b = PEDAL
    cx = (l + r) / 2
    for name, rad_pt, cy_pt in (("ui_knob_big@2x.png", 78, 129), ("ui_knob_small@2x.png", 55, 287)):
        frames, size, cap_img = render_knob_frames(rad_pt, px_center=(cx, t + cy_pt * S))
        strip_image(frames).save(os.path.join(out, name), optimize=True)
        cap_img.save(os.path.join(out, name.replace("knob", "cap")), optimize=True)
        print(name, size, "px per frame")
    strip_image(render_led()).save(os.path.join(out, "ui_led@2x.png"), optimize=True)
    print("done")


if __name__ == "__main__":
    main()
