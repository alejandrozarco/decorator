#!/usr/bin/env python3
"""Build the README / demo-page audio.

1. Plays short phrases from free sample sets, dry, at realistic instrument levels:
   - guitar: FreePATS "Electric Guitar FSBS (direct)", an unprocessed DI guitar (CC0 1.0)
     http://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html
   - Rhodes: jRhodes3d by Jeff Learman, a 1977 Rhodes Mark I Stage 73 (samples CC BY 4.0,
     music made with it CC0)  https://github.com/sfzinstruments/jlearman.jRhodes3d
   - drums: MuldjordKit by Lars Muldjord, FreePATS SFZ version (CC BY 4.0)
     http://freepats.zenvoid.org/Percussion/acoustic-drum-kit.html
2. Runs each phrase through the Decorator VST3 at a few Saturation settings.
3. Writes MP3s plus docs/demos.json (file list and loudness for the page's level-match toggle).

usage: make_demos.py --guitar DIR --rhodes DIR --drums DIR [--vst3 PATH] [--out docs/audio]
       (each DIR is the unpacked sample set, containing its .sfz)
needs: numpy scipy soundfile pedalboard, ffmpeg on PATH
"""
import argparse, json, os, re, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument("--guitar", required=True)
ap.add_argument("--rhodes", required=True, help="jRhodes3d checkout")
ap.add_argument("--drums", required=True, help="MuldjordKit SFZ+FLAC folder")
ap.add_argument("--vst3", default=os.path.expanduser("~/Library/Audio/Plug-Ins/VST3/Decorator.vst3"))
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "docs", "audio"))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
rng = np.random.default_rng(7)

# ---------- small SFZ player (key/vel ranges, round robins, note names, default_path) ----------
NOTE = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
def midi_of(v):
    v = v.strip()
    if re.fullmatch(r"-?\d+", v): return int(v)
    m = re.fullmatch(r"([a-gA-G])([#b]?)(-?\d+)", v)
    pc = NOTE[m.group(1).lower()] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + pc          # SFZ convention: C4 = 60

class SFZ:
    def __init__(self, path):
        self.dir = os.path.dirname(path); self.cache = {}; self.regions = []
        text = re.sub(r"//.*", "", open(path).read())
        dp = re.search(r"default_path=(\S+)", text); self.prefix = dp.group(1) if dp else ""
        group = {}
        for tag, body in re.findall(r"<(\w+)>([^<]*)", text):
            kv = dict(re.findall(r"(\w+)=(\S+)", body))
            if tag in ("group", "master", "global"): group = dict(kv); continue
            if tag != "region": continue
            r = {**group, **kv}
            if "key" in r:
                for k in ("lokey", "hikey", "pitch_keycenter"): r.setdefault(k, r["key"])
            self.regions.append(dict(lo=midi_of(r.get("lokey", "0")), hi=midi_of(r.get("hikey", "127")),
                                     key=midi_of(r.get("pitch_keycenter", r.get("lokey", "60"))),
                                     lovel=int(r.get("lovel", 0)), hivel=int(r.get("hivel", 127)),
                                     lorand=float(r.get("lorand", 0)), hirand=float(r.get("hirand", 1)),
                                     release=float(r.get("ampeg_release", 0.08)), sample=self.prefix + r["sample"]))
    def load(self, p):
        if p not in self.cache:
            x, sr = sf.read(os.path.join(self.dir, p.replace("\\", "/")), always_2d=True)
            x = x.mean(axis=1)
            if sr != SR: x = resample(x, int(len(x) * SR / sr))
            self.cache[p] = x
        return self.cache[p]
    def note(self, midi, vel, dur=None, ring=None, gain=None):
        """One note: pick the region (round robin by random), repitch, release after dur seconds (None = let ring)."""
        rr = rng.random()
        cand = [g for g in self.regions if g["lo"] <= midi <= g["hi"] and g["lovel"] <= vel <= g["hivel"]]
        cand = [g for g in cand if g["lorand"] <= rr < g["hirand"]] or cand
        g = cand[0]
        x = self.load(g["sample"])
        shift = midi - g["key"]
        if shift: x = resample(x, int(round(len(x) / 2 ** (shift / 12))))
        if dur is not None:
            ring = g["release"] if ring is None else ring
            n = min(len(x), int((dur + ring) * SR)); x = x[:n].copy()
            r = min(int(ring * SR), n); x[n - r:] *= np.linspace(1, 0, r) ** 2
        return x * (gain if gain is not None else 0.55 + 0.45 * vel / 127)

def find_sfz(d, prefer=None):
    c = sorted(os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith(".sfz"))
    if prefer: c = [p for p in c if os.path.basename(p) == prefer] or c
    return c[0]
GTR = SFZ(find_sfz(a.guitar))
RHO = SFZ(find_sfz(a.rhodes, "jRhodes3d-mono-no-xfade.sfz"))
DRM = SFZ(find_sfz(a.drums))
note = GTR.note

def render(events, length, inst=None):
    inst = inst or GTR
    y = np.zeros(int(length * SR) + 4 * SR)
    for t, midi, vel, dur in events:
        s = inst.note(midi, vel, dur); i = int(t * SR)
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

GROUP = {k: "Guitar" for k in P}

# 5. Rhodes: slow soul changes, voicings in the middle register, a little melody on top. 76 bpm
b = 60 / 76; ev = []
prog = [[53, 57, 60, 64, 67], [52, 55, 59, 62, 64], [50, 53, 57, 60, 64], [43, 53, 57, 59, 64]]  # Fmaj9 Em9 Dm9 G13
for bar, ch in enumerate(prog * 2):
    t0 = bar * 4 * b
    bass = ch[0] - 12
    ev.append((t0, bass, 92, 3.8 * b))
    for k, m in enumerate(ch[1:]):
        ev.append((t0 + 0.012 * k, m, 70 + 6 * (k % 2), 1.9 * b))          # chord on 1
        ev.append((t0 + 2.5 * b + 0.01 * k, m, 62 + 6 * (k % 2), 1.4 * b))  # push on the and of 3
mel = [(3.0, 72, .5), (3.5, 74, .5), (4.0, 76, 1.5), (7.0, 74, .5), (7.5, 72, .5), (8.0, 71, 2), (11.0, 69, .5), (11.5, 71, .5),
       (12.0, 72, 1), (13.0, 74, 1), (14.0, 71, 2), (19.0, 76, .5), (19.5, 79, .5), (20.0, 81, 1.5), (23.0, 79, .5), (23.5, 76, .5),
       (24.0, 74, 2), (27.0, 72, .5), (27.5, 74, .5), (28.0, 71, 4)]
ev += [(t * b, m, 96, d * b) for t, m, d in mel]
P["rhodes"] = ("Rhodes", render(ev, 8 * 4 * b + 3.0, RHO)); GROUP["rhodes"] = "Rhodes"

# 6. Drums: half-time groove, ghost notes, a fill and a crash. 92 bpm, hats in eighths
b = 60 / 92; ev = []
K, S, HC, HO, RIDE, CR, T1, T2, T4 = 48, 50, 52, 53, 54, 58, 61, 62, 64
for bar in range(4):
    t0 = bar * 4 * b
    for e in range(8):
        if bar == 3 and e >= 4: break
        ev.append((t0 + e * b / 2, HO if (bar == 1 and e == 7) else HC, 96 if e % 2 == 0 else 70, None))
    for t, v in ((0, 118), (1.5, 96), (2.75, 86)) if bar % 2 == 0 else ((0, 118), (0.75, 84), (2.5, 104)):
        ev.append((t0 + t * b, K, v, None))
    ev.append((t0 + 2 * b, S, 118, None))
    for t in (0.75, 3.25):
        ev.append((t0 + t * b, S, 34, None))           # ghost notes
fill = [(14.0, S, 100), (14.25, S, 80), (14.5, T1, 108), (14.75, T1, 96), (15.0, T2, 108), (15.25, T2, 96), (15.5, T4, 114), (15.75, T4, 104)]
ev += [(t * b, n, v, None) for t, n, v in fill]
ev += [(16 * b, CR, 124, None), (16 * b, K, 124, None)]
for bar in range(4, 6):
    t0 = bar * 4 * b
    for e in range(8): ev.append((t0 + e * b / 2, RIDE, 100 if e % 2 == 0 else 78, None))
    for t, v in ((0, 118), (1.5, 96), (2.75, 86)): ev.append((t0 + t * b, K, v, None))
    ev.append((t0 + 2 * b, S, 120, None))
ev += [(24 * b, CR, 124, None), (24 * b, K, 124, None)]
y = render(ev, 24 * b + 3.0, DRM)
P["drums"] = ("Drum kit", y); GROUP["drums"] = "Drums"

# ---------- levels: realistic dry signals, 0 dBFS = 12.5 dBu at the interface ----------
# guitar DI about -30 dBFS active RMS; Rhodes (hotter, line-ish pickup) -26; drum submix -24 (peaky)
TARGET = {"Guitar": -30.0, "Rhodes": -26.0, "Drums": -24.0}
def active_rms(x, n=2400):
    f = np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1) + 1e-20)
    return 20 * np.log10(np.sqrt(np.mean(f[f > f.max() * 10 ** (-30 / 20)] ** 2)))
for k, (name, x) in P.items():
    pk = 20 * np.log10(np.max(np.abs(x)))
    x *= 10 ** (min(TARGET[GROUP[k]] - active_rms(x), -1.0 - pk) / 20)   # never above -1 dBFS peak
    fade = int(0.3 * SR); x[-fade:] *= np.linspace(1, 0, fade)
    P[k] = (name, x)

# ---------- through the plugin ----------
import pedalboard as pb
plug = pb.load_plugin(a.vst3)
plug.interface_level_dbu = 12.5
SETTINGS = [("off", "Off (dry)", None, None), ("sat0900", "Saturation 9:00", "9:00", "12:00"),
            ("sat1030", "Saturation 10:30", "10:30", "12:00"), ("sat1200", "Saturation 12:00", "12:00", "12:00"),
            ("sat0130", "Saturation 1:30", "1:30", "12:00"), ("sat0300", "Saturation 3:00", "3:00", "12:00"),
            ("sat0500", "Saturation max", "5:00", "12:00")]
manifest = {"settings": [{"id": s[0], "label": s[1], "saturation": s[2], "volume": s[3]} for s in SETTINGS], "clips": []}
def mp3(x, path):
    tmp = path + ".wav"; sf.write(tmp, x.astype(np.float32), SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "192k", path], check=True); os.remove(tmp)
for k, (name, x) in P.items():
    clip = {"id": k, "title": name, "group": GROUP[k], "seconds": round(len(x) / SR, 2), "files": {}, "rms_db": {}}
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
