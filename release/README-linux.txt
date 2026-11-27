Decorator 0.1.0 for Linux (x86_64)

VST3:  copy  Decorator.vst3  to  ~/.vst3/
LV2:   copy  Decorator.lv2   to  ~/.lv2/
CLAP:  copy  Decorator.clap  to  ~/.clap/
(create the folder if it doesn't exist), then restart your DAW.

Your DAW draws the controls (no pedal graphics on Linux yet):
  Saturation and Volume: knob position in clock hours, 7 = 7:00 (min) ... 12 = 12:00 ... 17 = 5:00 (max).
                         13.5 means 1:30, 15 means 3:00.
  Interface level: your audio interface's input level at 0 dBFS, in dBu (12.5 for a Scarlett 3rd Gen
                   instrument input at minimum gain).
  Bypass.

Built on Ubuntu 22.04; needs glibc 2.35 or newer.
Source and help: https://github.com/alejandrozarco/decorator
