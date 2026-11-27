#pragma once
// Decorator: tape saturation built from ten NAM captures of a tape-saturation pedal.
// The Saturation knob crossfades between neighbouring captures; Volume is the measured
// post-saturation gain curve; Interface level calibrates the in/out levels in dBu.

#include <array>
#include <atomic>
#include <memory>
#include <vector>

#include "IPlug_include_in_plug_hdr.h"

#include "DecoratorEngine.h"

const int kNumPresets = 1;

enum EParams
{
  kSaturation = 0, // knob position in clock hours, 7 (min) .. 17 (max)
  kVolume,         // knob position in clock hours, 7 .. 17
  kInterfaceDbu,   // interface input level at 0 dBFS
  kBypass,
  kNumParams
};

enum ECtrlTags
{
  kCtrlTagStatus = 0,
  kNumCtrlTags
};

class Decorator final : public iplug::Plugin
{
public:
  Decorator(const iplug::InstanceInfo& info);

  void ProcessBlock(iplug::sample** inputs, iplug::sample** outputs, int nFrames) override;
  void OnReset() override;
  void OnIdle() override;

private:
  decorator::Params _Params() const;

  decorator::Engine mEngine;
  WDL_String mStatus;
};
