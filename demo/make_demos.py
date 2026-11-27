#!/usr/bin/env python3
"""Build the README / demo-page audio.

1. Plays short guitar phrases from the FreePATS "Electric Guitar FSBS (direct)" sample bank
   (CC0 1.0, http://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html), i.e. an
   unprocessed DI guitar, at a realistic instrument level.
2. Runs each phrase through the Decorator VST3 at a few Saturation settings.
3. Writes MP3s plus docs/demos.json (file list and loudness for the page's level-match toggle).

usage: make_demos.py PATH/TO/"EGuitarFSBS-direct SFZ+FLAC-20220911" [--vst3 PATH] [--out docs/audio]
needs: numpy scipy soundfile pedalboard, ffmpeg on PATH
"""
import argparse, json, os, re, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument("bank")
ap.add_argument("--vst3", default=os.path.expanduser("~/Library/Audio/Plug-Ins/VST3/Decorator.vst3"))
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "docs", "audio"))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
rng = np.random.default_rng(7)

# ---------- minimal SFZ reader (only what this bank uses) ----------
sfz = open([os.path.join(a.bank, f) for f in os.listdir(a.bank) if f.endswith(".sfz")][0]).read()
sfz = re.sub(r"//.*", "", sfz)
groups = []
for g in sfz.split("<group>")[1:]:
    head, *regions = g.split("<region>")
    kv = dict(re.findall(r"(\w+)=(\S+)", head))
    samples = [dict(re.findall(r"(\w+)=(\S+)", r))["sample"] for r in regions]
    if "key" in kv: kv.setdefault("lokey", kv["key"]); kv.setdefault("hikey", kv["key"]); kv.setdefault("pitch_keycenter", kv["key"])
    groups.append(dict(lo=int(kv["lokey"]), hi=int(kv["hikey"]), lovel=int(kv.get("lovel", 0)),
                       hivel=int(kv.get("hivel", 127)), key=int(kv["pitch_keycenter"]), samples=samples))
cache = {}
def load(path):
    if path not in cache:
        x, sr = sf.read(os.path.join(a.bank, path), always_2d=True)
        x = x.mean(axis=1)
        if sr != SR: x = resample(x, int(len(x) * SR / sr))
        cache[path] = x
    return cache[path]

def note(midi, vel, dur, ring=0.08):
    """One plucked note: pick a round-robin sample, repitch, damp after dur seconds."""
    cand = [g for g in groups if g["lo"] <= midi <= g["hi"] and g["lovel"] <= vel <= g["hivel"]]
    g = cand[0]
    x = load(g["samples"][rng.integers(len(g["samples"]))])
    shift = midi - g["key"]
    if shift: x = resample(x, int(round(len(x) / 2 ** (shift / 12))))
    n = min(len(x), int((dur + ring) * SR))
    x = x[:n].copy()
    r = min(int(ring * SR), n)
    x[n - r:] *= np.linspace(1, 0, r) ** 2            # finger damping
    return x * (0.55 + 0.45 * vel / 127)

def render(events, length):
    y = np.zeros(int(length * SR) + SR)
    for t, midi, vel, dur in events:
        s = note(midi, vel, dur); i = int(t * SR)
        y[i:i + len(s)] += s[: len(y) - i]
    return y[: int(length * SR)]

def strum(t, chord, vel, dur, up=False, gap=0.011):
    notes = chord[::-1] if up else chord
    return [(t + k * gap * (1 + 0.2 * rng.random()), m, max(1, vel - (k * 3 if up else 0)), dur - k * gap) for k, m in enumerate(notes)]

# ---------- phrases ----------
P = {}
# 1. open-chord strumming, Em C G D at 84 bpm
b = 60 / 84; ev = []
for bar, ch in enumerate([[40, 47, 52, 55, 59, 64], [48, 52, 55, 60, 64], [43, 47, 50, 55, 59, 67], [50, 57, 62, 66]] * 2):
    t0 = bar * 4 * b
    for beat, up, v in ((0, 0, 118), (1, 0, 100), (1.5, 1, 80), (2.5, 1, 82), (3, 0, 104), (3.5, 1, 84)):
        nxt = [1, 1.5, 2.5, 3, 3.5, 4][[0, 1, 1.5, 2.5, 3, 3.5].index(beat)]
        ev += strum(t0 + beat * b, ch, v, (nxt - beat) * b - 0.01, bool(up))
P["chords"] = ("Open chords", render(ev, 8 * 4 * b + 1.5))
# 2. picked arpeggios, Am F C G at 96 bpm, notes ring over the bar
b = 60 / 96; ev = []
for bar, ch in enumerate([[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [48, 52, 55, 60, 64], [43, 47, 50, 55, 59]] * 2):
    order = [0, 2, 3, 4, 3, 2, 1, 2]
    for k, idx in enumerate(order):
        ev.append((bar * 4 * b + k * b / 2, ch[idx], 92 + 20 * (k % 4 == 0), 4 * b - k * b / 2))
P["arpeggios"] = ("Arpeggios", render(ev, 8 * 4 * b + 2.0))
# 3. single-note lead line, A minor pentatonic, 100 bpm
b = 60 / 100
line = [(0, 69, 1), (1, 72, .5), (1.5, 74, .5), (2, 76, 1.5), (3.5, 74, .5), (4, 72, .5), (4.5, 69, .5), (5, 72, 1), (6, 67, 2),
        (8, 64, .5), (8.5, 67, .5), (9, 69, .5), (9.5, 72, .5), (10, 74, .75), (10.75, 76, .25), (11, 79, 1), (12, 76, .5), (12.5, 74, .5),
        (13, 72, .5), (13.5, 69, .5), (14, 72, .5), (14.5, 74, .5), (15, 69, 3)]
P["lead"] = ("Lead line", render([(t * b, m, 112, d * b) for t, m, d in line], 18 * b + 2.0))
# 4. low-string riff with short, muted eighths and power chords, 112 bpm
b = 60 / 112; ev = []
for rep in range(4):
    t0 = rep * 4 * b
    for k in range(6): ev.append((t0 + k * b / 2, 40, 100 + 15 * (k == 0), b / 2 * 0.45))
    ev += strum(t0 + 3 * b, [43, 50, 55], 120, b * 0.95, gap=0.008)
    ev += strum(t0 + 3.5 * b, [45, 52, 57] if rep % 2 == 0 else [38, 45, 50], 120, b * 0.5, gap=0.008)
ev += strum(16 * b, [40, 47, 52], 124, 4 * b, gap=0.008)
P["riff"] = ("Low riff", render(ev, 20 * b + 1.0))

# ---------- level: a typical single-coil DI, about -30 dBFS active RMS at 12.5 dBu = 0 dBFS ----------
def active_rms(x, n=2400):
    f = np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1) + 1e-20)
    return 20 * np.log10(np.sqrt(np.mean(f[f > f.max() * 10 ** (-30 / 20)] ** 2)))
for k, (name, x) in P.items():
    x *= 10 ** ((-30 - active_rms(x)) / 20)
    fade = int(0.3 * SR); x[-fade:] *= np.linspace(1, 0, fade)
    P[k] = (name, x)

# ---------- through the plugin ----------
import pedalboard as pb
plug = pb.load_plugin(a.vst3)
plug.interface_level_dbu = 12.5
SETTINGS = [("off", "Off (clean DI)", None, None), ("sat0900", "Saturation 9:00", "9:00", "12:00"),
            ("sat1200", "Saturation 12:00", "12:00", "12:00"), ("sat0300", "Saturation 3:00", "3:00", "12:00"),
            ("sat0500", "Saturation max", "5:00", "12:00")]
manifest = {"settings": [{"id": s[0], "label": s[1], "saturation": s[2], "volume": s[3]} for s in SETTINGS], "clips": []}
def mp3(x, path):
    tmp = path + ".wav"; sf.write(tmp, x.astype(np.float32), SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "192k", path], check=True); os.remove(tmp)
for k, (name, x) in P.items():
    clip = {"id": k, "title": name, "seconds": round(len(x) / SR, 2), "files": {}, "rms_db": {}}
    for sid, label, sat, vol in SETTINGS:
        if sat is None: y = x
        else:
            plug.reset(); plug.bypass = False; plug.saturation = sat; plug.volume = vol
            lat = 26
            y = plug.process(np.concatenate([x, np.zeros(lat)]).astype(np.float32)[None, :], SR)[0].astype(np.float64)[lat:]
        pk = np.max(np.abs(y))
        assert pk < 1.0, (k, sid, pk)
        fn = f"{k}_{sid}.mp3"; mp3(y, os.path.join(a.out, fn))
        clip["files"][sid] = "audio/" + fn; clip["rms_db"][sid] = round(float(active_rms(y)), 2)
    manifest["clips"].append(clip); print(k, clip["rms_db"])
json.dump(manifest, open(os.path.join(a.out, "..", "demos.json"), "w"), indent=1)
