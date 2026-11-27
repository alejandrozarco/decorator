// DPF wrapper for Decorator (Linux VST3 / LV2 / CLAP). Same DSP as the iPlug2 plugin: ../Decorator/DecoratorEngine.h
#pragma once

#define DISTRHO_PLUGIN_BRAND   "Decorator"
#define DISTRHO_PLUGIN_NAME    "Decorator"
#define DISTRHO_PLUGIN_URI     "https://github.com/alejandrozarco/decorator"
#define DISTRHO_PLUGIN_CLAP_ID "com.decorator-plugin.decorator"

#define DISTRHO_PLUGIN_BRAND_ID  Dcrp
#define DISTRHO_PLUGIN_UNIQUE_ID Dcrt

#define DISTRHO_PLUGIN_HAS_UI        0
#define DISTRHO_PLUGIN_IS_RT_SAFE    1
#define DISTRHO_PLUGIN_NUM_INPUTS    2
#define DISTRHO_PLUGIN_NUM_OUTPUTS   2
#define DISTRHO_PLUGIN_WANT_LATENCY  1
#define DISTRHO_PLUGIN_LV2_CATEGORY  "lv2:DistortionPlugin"
#define DISTRHO_PLUGIN_VST3_CATEGORIES "Fx|Distortion"
#define DISTRHO_PLUGIN_CLAP_FEATURES "audio-effect", "distortion", "stereo"
