#!/usr/bin/env python3
"""Build the README / demo-page audio.

1. Plays short phrases from free sample sets, dry, at realistic instrument levels:
   - guitar: FreePATS "Electric Guitar FSBS (direct)", an unprocessed DI guitar (CC0 1.0)
     http://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html
   - Rhodes: jRhodes3d by Jeff Learman, a 1977 Rhodes Mark I Stage 73 (samples CC BY 4.0,
     music made with it CC0)  https://github.com/sfzinstruments/jlearman.jRhodes3d
   - drums: MuldjordKit by Lars Muldjord, FreePATS SFZ version (CC BY 4.0)
     http://freepats.zenvoid.org/Percussion/acoustic-drum-kit.html
   - organ: a tonewheel organ synthesized here (additive drawbars, percussion, key click, no rotary speaker)
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
                                     release=float(r.get("ampeg_release", 0.08)), sample=self.prefix + r["sample"],
                                     loop=(int(r["loop_start"]), int(r["loop_end"])) if r.get("loop_mode") == "loop_continuous" and "loop_start" in r else None,
                                     sr=None))
    def rate(self, p):
        return sf.info(os.path.join(self.dir, p.replace("\\", "/"))).samplerate
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
        if g["loop"] and dur is not None:            # sustain by repeating the loop (loop points are at the file's rate)
            ls, le = g["loop"]; ratio = SR / self.rate(g["sample"]); ls, le = int(ls * ratio), int(le * ratio)
            need = int((dur + 1.0) * SR * 2 ** ((midi - g["key"]) / 12))
            if need > len(x) and le > ls:
                reps = (need - le) // (le - ls) + 2
                x = np.concatenate([x[:le]] + [x[ls:le]] * reps)
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
class Tonewheel:
    """Additive tonewheel organ, no rotary speaker: nine drawbars (16' 5 1/3' 8' 4' 2 2/3' 2' 1 3/5' 1 1/3' 1'),
    3rd-harmonic percussion, key click, foldback of the top wheels, slightly impure wheel waveforms."""
    RATIOS = [0.5, 1.5, 1, 2, 3, 4, 5, 6, 8]
    def __init__(self, drawbars="888400000", percussion=True):
        self.amp = [0.0 if c == "0" else 10 ** (-3 * (8 - int(c)) / 20) for c in drawbars]
        self.perc = percussion
    def note(self, midi, vel, dur=None, ring=None, gain=None):
        dur = 1.0 if dur is None else dur
        n = int((dur + 0.02) * SR); t = np.arange(n) / SR
        f0 = 440.0 * 2 ** ((midi - 69) / 12); y = np.zeros(n)
        for r, a in zip(self.RATIOS, self.amp):
            if a == 0: continue
            f = f0 * r
            while f > 5900: f /= 2                       # the top tonewheels fold back an octave
            ph = rng.random() * 2 * np.pi
            w = np.sin(2 * np.pi * f * t + ph)
            y += a * (w + 0.03 * np.sin(2 * (2 * np.pi * f * t + ph)))   # wheels aren't perfect sines
        if self.perc:                                    # 3rd-harmonic percussion, fast decay
            y += 0.7 * np.sin(2 * np.pi * f0 * 3 * t) * np.exp(-t / 0.18)
        att, rel = int(0.004 * SR), int(0.012 * SR)
        env = np.ones(n); env[:att] = np.linspace(0, 1, att); env[n - rel:] = np.linspace(1, 0, rel)
        y *= env
        click = rng.standard_normal(int(0.003 * SR)) * np.hanning(int(0.003 * SR)) * 0.08   # key contact click
        y[:len(click)] += click
        return y * 0.25
ORG = Tonewheel("888400000", percussion=True)
ORG_FULL = Tonewheel("888888888", percussion=False)
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

# 5b. Organ: big rock chords, power-chord voicings (root, fifth, octave, fifth above) in the middle register.
#     C - Eb - F with syncopated pushes, a bar of staccato hits, a palm-slide glissando down the white keys,
#     and the final chord with every drawbar out. 116 bpm.
b = 60 / 116
V = {"C": [48, 55, 60, 67, 72], "Eb": [51, 58, 63, 70, 75], "F": [53, 60, 65, 72, 77], "Bb": [46, 53, 58, 65, 70]}
def chord(ev, beat, c, ln, v):
    for k, m in enumerate(V[c]): ev.append((beat * b + 0.004 * k, m, v, ln * b))
A = [(0, "C", 0.45, 120), (0.75, "C", 0.2, 104), (1.5, "Eb", 0.95, 118), (2.5, "Eb", 0.2, 100), (3, "F", 0.4, 116),
     (3.5, "F", 1.9, 122), (5.5, "Eb", 0.4, 110), (6, "C", 0.45, 118), (6.75, "C", 0.2, 102), (7.5, "Bb", 0.45, 114)]
ev = []
for t0 in (0, 16):                                   # phrase A twice
    for beat, c, ln, v in A: chord(ev, t0 + beat, c, ln, v)
for k in range(8):                                   # staccato bar, accents on 1 and 3
    chord(ev, 8 + 0.5 * k, "C", 0.18, 122 if k % 4 == 0 else (108 if k % 2 == 0 else 96))
chord(ev, 12, "Eb", 1.4, 120); chord(ev, 13.5, "F", 2.4, 124)
for k in range(6):                                   # second staccato bar, on F, then the turnaround
    chord(ev, 24 + 0.5 * k, "F", 0.18, 120 if k % 4 == 0 else 100)
chord(ev, 27, "Eb", 0.45, 116); chord(ev, 28, "Bb", 0.9, 118); chord(ev, 29, "F", 0.9, 120)
whites = [m for m in range(84, 59, -1) if m % 12 in (0, 2, 4, 5, 7, 9, 11)]   # C6 down to C4
g0, g1 = 30.0, 31.85
gl = []
for k, m in enumerate(whites):                       # palm slide: accelerating run down the keys
    tb = g0 + (g1 - g0) * (k / (len(whites) - 1)) ** 0.8
    gl.append((tb * b, m, 110 - 2 * k, 0.12 * b))
y = render(ev, 38 * b + 1.5, ORG) + 10 ** (4 / 20) * render(gl, 38 * b + 1.5, ORG)
fin = []
for m in V["C"] + [79]: fin.append((32 * b, m, 124, 6 * b))
y = y + 10 ** (-4.5 / 20) * render(fin, 38 * b + 1.5, ORG_FULL)   # every drawbar out for the last chord
P["organ"] = ("Organ chords", y); GROUP["organ"] = "Organ"

# 6. Drums: dense funk groove, 16th hats, no crashes (sustained energy rather than a few loud peaks). 100 bpm
b = 60 / 100; ev = []
K, S, HC, HO, RIDE, T1, T2, T4 = 48, 50, 52, 53, 54, 61, 62, 64
kicks = [[0, 0.75, 1.5, 2.5, 3.25], [0, 0.5, 1.75, 2.5, 3.0]]
for bar in range(8):
    t0 = bar * 4 * b
    last = bar == 7
    for e in range(16):
        if last and e >= 12: break
        acc = e % 4 == 0
        ev.append((t0 + e * b / 4, HO if (e == 14 and bar % 2 == 1) else HC, 92 if acc else (76 if e % 2 == 0 else 60), None))
    for t in kicks[bar % 2]:
        ev.append((t0 + t * b, K, 112 if t == 0 else 100, None))
    for t in (1, 3):
        if not (last and t == 3): ev.append((t0 + t * b, S, 114, None))
    for t in (1.75, 2.25, 3.75):
        if not (last and t > 3): ev.append((t0 + t * b, S, 40, None))          # ghost notes
fill = [(3.0, S, 104), (3.25, S, 92), (3.5, T1, 108), (3.625, T1, 96), (3.75, T2, 108), (3.875, T4, 110)]
ev += [(7 * 4 * b + t * b, n, v, None) for t, n, v in fill]
ev += [(32 * b, K, 116, None), (32 * b, HO, 100, None)]
y = render(ev, 32 * b + 2.0, DRM)
P["drums"] = ("Drum kit", y); GROUP["drums"] = "Drums"

# ---------- levels: realistic dry signals, 0 dBFS = 12.5 dBu at the interface ----------
# guitar DI about -30 dBFS active RMS; Rhodes (hotter, line-ish pickup) -26; drum submix -24 (peaky)
TARGET = {"Guitar": -30.0, "Rhodes": -26.0, "Organ": -26.0, "Drums": -24.0}
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
VOLUME = {"Guitar": "12:00", "Rhodes": "12:00", "Organ": "12:00", "Drums": "2:30"}   # drums hit the pedal hard; turn Volume up as you would on the pedal
for k, (name, x) in P.items():
    clip = {"id": k, "title": name, "group": GROUP[k], "volume": VOLUME[GROUP[k]], "seconds": round(len(x) / SR, 2), "files": {}, "rms_db": {}}
    for sid, label, sat, vol in SETTINGS:
        if sat is None: y = x
        else:
            plug.reset(); plug.bypass = False; plug.saturation = sat; plug.volume = VOLUME[GROUP[k]]
            lat = 26
            y = plug.process(np.concatenate([x, np.zeros(lat)]).astype(np.float32)[None, :], SR)[0].astype(np.float64)[lat:]
        pk = np.max(np.abs(y))
        assert pk < 1.0, (k, sid, pk)
        fn = f"{k}_{sid}.mp3"; mp3(y, os.path.join(a.out, fn))
        clip["files"][sid] = "audio/" + fn; clip["rms_db"][sid] = round(float(active_rms(y)), 2)
    manifest["clips"].append(clip); print(k, clip["rms_db"])
json.dump(manifest, open(os.path.join(a.out, "..", "demos.json"), "w"), indent=1)
