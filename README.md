<p><b>⬇ Download:</b> <a href="https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-macOS.pkg"><b>macOS installer</b></a> &nbsp;·&nbsp; <a href="https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-VST3-Windows.zip"><b>Windows VST3</b></a> &nbsp;·&nbsp; <a href="https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-VST3-Linux.zip"><b>Linux VST3</b></a> &nbsp;·&nbsp; <a href="https://alejandrozarco.github.io/decorator/"><b>▶ Live demos</b></a> &nbsp;·&nbsp; <a href="#install">Install steps</a></p>

<img src="docs/img/decorator-small.png" alt="Decorator plugin: brushed-steel pedal with Saturation and Volume knobs" width="150" align="right">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/logo-dark.png">
  <img src="docs/img/logo.png" alt="Decorator" width="330">
</picture>

**Tape saturation from neural captures of a real pedal.** Free VST3 for macOS, Windows and Linux, plus AU and standalone apps.

<br clear="right">

## Install

| | Download | Install |
|---|---|---|
| **macOS** 12+ (Apple silicon and Intel) | **[Decorator-macOS.pkg](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-macOS.pkg)**: AU, VST3 and app | Double-click it. If macOS says it *can't verify the developer*, click **Done**, open **System Settings → Privacy & Security**, and click **Open Anyway**. Then click through the installer. |
| **Windows** 10/11, 64-bit | **[Decorator-VST3-Windows.zip](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-VST3-Windows.zip)** ([with standalone app](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-Windows.zip)) | Unzip it, then copy the `Decorator.vst3` folder into `C:\Program Files\Common Files\VST3`. If SmartScreen warns, click **More info → Run anyway**. |
| **Linux** x86_64 | **[Decorator-VST3-Linux.zip](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-VST3-Linux.zip)** ([VST3 + LV2 + CLAP](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-Linux.zip)) | Unzip it, then copy `Decorator.vst3` into `~/.vst3`. LV2 goes in `~/.lv2` and CLAP in `~/.clap`. |

Then restart your DAW. The plugin is listed as **Decorator** under the manufacturer **Decorator**. In Logic Pro: Audio FX → Audio Units → Decorator.

<sub>Mac, single formats: [VST3](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-VST3-macOS.zip) · [AU](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-AU-macOS.zip) · [app](https://github.com/alejandrozarco/decorator/releases/latest/download/Decorator-App-macOS.zip). Each zip has a READ ME with a one-line Terminal command to unblock it. The files aren't signed with a paid Apple or Microsoft developer account, so the system warns once. Linux hosts show standard controls instead of the pedal graphics. Also: [the same captures as TONE3000 profiles](https://www.tone3000.com/tones/113208) · [all releases](https://github.com/alejandrozarco/decorator/releases) · [uninstall](#uninstall)</sub>

## What it is

Decorator is a guitar plugin that recreates a digital tape-saturation stompbox from 2014. The pedal has two knobs on its saturation side:

- **Saturation** runs from almost clean, slightly thickened tape at 7:00 to heavy, compressed tape drive at full.
- **Volume** sets the output level.

The plugin has the same two knobs and a bypass footswitch, on a brushed-steel face.

Behind the knobs are **ten [Neural Amp Modeler](https://github.com/sdatkinson/neural-amp-modeler) A2 captures** of the real pedal. They were taken at Saturation 7:00, 8:30, 9:00, 10:00, 11:00, 12:00, 1:00, 2:00, 3:00 and 4:00, with Volume at maximum. The captures are embedded in the plugin, so there are no files to load.

## The TONE3000 version

The same ten captures are also on TONE3000 as a pack of NAM profiles: **[tone3000.com/tones/113208](https://www.tone3000.com/tones/113208)**.

| | TONE3000 pack | Decorator plugin |
|---|---|---|
| Captures | the same ten NAM A2 models | the same ten, embedded |
| Saturation | ten fixed steps: load one profile per setting | a continuous knob that crossfades neighbouring captures |
| Volume | output level fixed to roughly the pedal's Volume at 12:45 | the full Volume knob, using the measured curve |
| Runs in | any NAM host (TONE3000, NAM plugin, ...) | its own AU / VST3 / app |

At a capture position the plugin runs exactly the same model as the matching TONE3000 profile. With Volume at max (and output levels lined up), the two null below −90 dB. With Volume at about 12:40, the plugin's level is within 0.1 dB of the TONE3000 profile's. The pack is the easiest way to use one setting in a NAM rig. The plugin adds the knobs between the steps.

## Listen

<p align="center"><img src="docs/img/settings.png" alt="Five of the demo settings: bypassed, then Saturation 9:00, 12:00, 3:00 and max" width="640"></p>

**[▶ Open the live demo page](https://alejandrozarco.github.io/decorator/)** to play each clip and switch between the clean DI and the plugin while it keeps playing. The page can also match loudness, or add a simple speaker filter. The page source is in [`docs/`](docs/index.html). To run it locally, use `python3 -m http.server` inside `docs/`.

Or download the MP3s. Volume is at 12:00, except 2:30 for the drums, and the levels are real, not loudness-matched:

| Clip | Dry | Sat 9:00 | Sat 10:30* | Sat 12:00 | Sat 1:30* | Sat 3:00 | Sat max |
|---|---|---|---|---|---|---|---|
| Guitar: Open chords | [▶](docs/audio/chords_off.mp3) | [▶](docs/audio/chords_sat0900.mp3) | [▶](docs/audio/chords_sat1030.mp3) | [▶](docs/audio/chords_sat1200.mp3) | [▶](docs/audio/chords_sat0130.mp3) | [▶](docs/audio/chords_sat0300.mp3) | [▶](docs/audio/chords_sat0500.mp3) |
| Guitar: Arpeggios | [▶](docs/audio/arpeggios_off.mp3) | [▶](docs/audio/arpeggios_sat0900.mp3) | [▶](docs/audio/arpeggios_sat1030.mp3) | [▶](docs/audio/arpeggios_sat1200.mp3) | [▶](docs/audio/arpeggios_sat0130.mp3) | [▶](docs/audio/arpeggios_sat0300.mp3) | [▶](docs/audio/arpeggios_sat0500.mp3) |
| Guitar: Lead line | [▶](docs/audio/lead_off.mp3) | [▶](docs/audio/lead_sat0900.mp3) | [▶](docs/audio/lead_sat1030.mp3) | [▶](docs/audio/lead_sat1200.mp3) | [▶](docs/audio/lead_sat0130.mp3) | [▶](docs/audio/lead_sat0300.mp3) | [▶](docs/audio/lead_sat0500.mp3) |
| Guitar: Low riff | [▶](docs/audio/riff_off.mp3) | [▶](docs/audio/riff_sat0900.mp3) | [▶](docs/audio/riff_sat1030.mp3) | [▶](docs/audio/riff_sat1200.mp3) | [▶](docs/audio/riff_sat0130.mp3) | [▶](docs/audio/riff_sat0300.mp3) | [▶](docs/audio/riff_sat0500.mp3) |
| Rhodes: Rhodes | [▶](docs/audio/rhodes_off.mp3) | [▶](docs/audio/rhodes_sat0900.mp3) | [▶](docs/audio/rhodes_sat1030.mp3) | [▶](docs/audio/rhodes_sat1200.mp3) | [▶](docs/audio/rhodes_sat0130.mp3) | [▶](docs/audio/rhodes_sat0300.mp3) | [▶](docs/audio/rhodes_sat0500.mp3) |
| Organ: Organ groove | [▶](docs/audio/organ_off.mp3) | [▶](docs/audio/organ_sat0900.mp3) | [▶](docs/audio/organ_sat1030.mp3) | [▶](docs/audio/organ_sat1200.mp3) | [▶](docs/audio/organ_sat0130.mp3) | [▶](docs/audio/organ_sat0300.mp3) | [▶](docs/audio/organ_sat0500.mp3) |
| Drums: Drum kit | [▶](docs/audio/drums_off.mp3) | [▶](docs/audio/drums_sat0900.mp3) | [▶](docs/audio/drums_sat1030.mp3) | [▶](docs/audio/drums_sat1200.mp3) | [▶](docs/audio/drums_sat0130.mp3) | [▶](docs/audio/drums_sat0300.mp3) | [▶](docs/audio/drums_sat0500.mp3) |

\* Between capture positions: the plugin crossfades the 10:00/11:00 and 1:00/2:00 captures here.

Demo sounds: guitar from the [FreePATS "Electric Guitar FSBS (direct)"](http://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html) bank, a raw DI recording of a Fender guitar (**CC0**). Rhodes from [jRhodes3d](https://github.com/sfzinstruments/jlearman.jRhodes3d) by Jeff Learman, a 1977 Rhodes Mark I Stage 73 (samples CC BY 4.0, music made with them CC0). Drums from [MuldjordKit](http://freepats.zenvoid.org/Percussion/acoustic-drum-kit.html) by Lars Muldjord (**CC BY 4.0**). Organ from the FreePATS [percussive organ](http://freepats.zenvoid.org/Organ/electric-organ.html) bank, a tonewheel organ sampled from the setBfree emulator (**CC0**). The phrases are played dry at realistic levels (guitar about −30 dBFS RMS, Rhodes and organ −26, drums peaking at −1 dBFS), then run through the plugin alone, with no amp or cab. `demo/make_demos.py` rebuilds everything.

## How it works

- **Saturation**: between capture positions, the plugin crossfades the two neighbouring captures. Only those two run, so CPU use stays at about one model. The real pedal does nothing between 7:00 and 8:00 or between 4:00 and 5:00, and the plugin copies that. The captures' latencies (21–26 samples) are evened out so the crossfades don't comb-filter.
- **Volume**: a gain curve fitted through levels measured on the pedal at 7:00, 9:00, 12:00, 3:00 and 5:00, plus one estimated point near 10:15. 5:00 is unity relative to the captures. 12:00 is about −9.7 dB.
- **Calibration**: the captures expect a particular voltage at the input. Set **Interface dBu** in the footer to your audio interface's input level at 0 dBFS. The default is 12.5 dBu, which is a Focusrite Scarlett 3rd Gen instrument input at minimum gain. The plugin then drives the model as hard as the real pedal would be driven, and returns the result at the pedal's real output level.
- **Mono in, mono out to both channels**. 26 samples of reported latency, and the bypass path is delayed to match, so the footswitch doesn't click.

## How close is it?

These were measured against the real pedal through the same interface:

| Test | Result |
|---|---|
| Reamped DI through the pedal vs. the capture at Sat 9:00, 12:00, 3:00 (Volume max) | Difference signal −24 to −29 dB below the output, level within 0.4 dB |
| Played live, same chords clean and through the pedal, Sat max, Volume 12:00, into two different amp models | Level within 0.4 dB, EQ shape within 0.8 dB RMS (2 dB max) |
| Plugin vs. the bare NAM capture at every capture position | Nulls to −91 dB or lower, i.e. identical |

Not modelled: the pedal's other half (a tape doubler/echo), and its hiss. The real unit's noise floor is about −72 dBFS. Saturation settings between capture positions are crossfades and haven't been checked against the pedal yet.

## Uninstall

Delete these and restart your DAW:
- `Decorator.component` from `/Library/Audio/Plug-Ins/Components` or `~/Library/Audio/Plug-Ins/Components`
- `Decorator.vst3` from `/Library/Audio/Plug-Ins/VST3` or `~/Library/Audio/Plug-Ins/VST3`
- `Decorator.app` from Applications

If you chose "Install for me only", the files are in the `~/Library` folders and `~/Applications`.

## Troubleshooting

- **The plugin doesn't show up**: quit your DAW completely and open it again. In Logic, open **Logic Pro → Settings → Plug-in Manager**, select Decorator and click **Reset & Rescan Selection**.
- **"Decorator.pkg can't be opened"**: see step 2 above. macOS shows this for any installer that isn't signed with a paid Apple developer account. The source code is all here if you'd rather build it yourself.
- **Too quiet or too distorted**: set **Interface dBu** at the bottom of the plugin to your interface's input level at 0 dBFS. Your interface's spec sheet lists it as the maximum instrument input level (at minimum gain). For example, it's 12.5 dBu for a Focusrite Scarlett 3rd Gen.

## Build from source

```bash
git clone --recurse-submodules <this repo>
cd decorator
source/iPlug2/Dependencies/IPlug/download-iplug-sdks.sh        # VST3 SDK
cd source/Decorator
xcodebuild -project projects/Decorator-macOS.xcodeproj -scheme macOS-AUv2 \
  -configuration Release -arch arm64 CODE_SIGN_IDENTITY="-" CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM=""
```

Use the schemes `macOS-VST3` and `macOS-APP` for the other formats. The build copies its output to `~/Library/Audio/Plug-Ins` (AU and VST3) and `~/Applications`. Without a developer certificate the build is ad-hoc signed. That's fine on the machine that built it.

### Regenerating assets

| What | Script | Output |
|---|---|---|
| UI bitmaps (brushed steel, knobs, footswitch, LED) lit from height maps | `source/Decorator/scripts/render_ui.py` | `resources/img/ui_*@2x.png` |
| Embed bitmaps in the binary | `source/Decorator/scripts/embed_assets.py` | `DecoratorAssets.inc` |
| README / demo page images | `demo/make_images.py` | `docs/img/` |
| Demo audio | `demo/make_demos.py --guitar … --rhodes … --drums …` | `docs/audio/`, `docs/demos.json` |

Python needs `numpy scipy pillow soundfile pedalboard`, and `ffmpeg` must be installed for the audio.

To make the installer and zip that go on a release, run `release/make_release.sh 0.1.0`. The output lands in `release/dist/`.

## Layout

```
source/                   everything needed to build
  Decorator/              plugin source (iPlug2 project)
    Decorator.cpp/.h      DSP, crossfade, volume curve, UI
    DecoratorModels.inc   the ten captures (NAM JSON)
    DecoratorAssets.inc   pre-rendered UI bitmaps
    scripts/              UI renderer, asset embedder, iPlug2 build helpers
  iPlug2, NeuralAmpModelerCore, AudioDSPTools, eigen   submodules
release/                  make_release.sh: universal build + .pkg installer + zip
demo/                     scripts for the demo audio and images
docs/                     live demo page, audio, images
```

## Licence

Decorator is free software under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).

It's built on:
- [NeuralAmpModelerPlugin](https://github.com/sdatkinson/NeuralAmpModelerPlugin), [NeuralAmpModelerCore](https://github.com/sdatkinson/NeuralAmpModelerCore) and [AudioDSPTools](https://github.com/sdatkinson/AudioDSPTools), © Steven Atkinson, MIT. The original notice is in [LICENSE-MIT-NeuralAmpModeler.txt](source/LICENSE-MIT-NeuralAmpModeler.txt).
- [iPlug2](https://github.com/iPlug2/iPlug2) (zlib-style licence), [Eigen](https://eigen.tuxfamily.org) (MPL 2.0) and the VST3 SDK (MIT).
- The fonts Montserrat, Archivo Black and Michroma (SIL OFL 1.1) and Roboto (Apache 2.0).
- Demo audio sources: FreePATS Electric Guitar FSBS (direct), CC0 1.0. jRhodes3d by Jeff Learman (samples CC BY 4.0). MuldjordKit by Lars Muldjord, FreePATS version (CC BY 4.0). FreePATS Percussive organ emulation (CC0 1.0).

The pedal name and maker are left out on purpose. This project isn't affiliated with or endorsed by any pedal manufacturer.
