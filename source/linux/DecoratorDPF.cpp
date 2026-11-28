// Decorator as a DPF plugin. Hosts show their own controls for the four parameters.
#include "DistrhoPlugin.hpp"
#include "../Decorator/DecoratorEngine.h"

START_NAMESPACE_DISTRHO

class DecoratorPlugin : public Plugin
{
public:
  enum { kSaturation, kVolume, kInterfaceDbu, kBypass, kNumParams };

  DecoratorPlugin()
  : Plugin(kNumParams, 0, 0)
  {
    setLatency(decorator::Engine::Latency());
  }

protected:
  const char* getLabel() const override { return "Decorator"; }
  const char* getDescription() const override
  {
    return "Tape saturation from ten neural captures of a real pedal. Saturation crossfades the captures; "
           "Volume follows the curve measured on the pedal; set Interface level to your interface's input level "
           "at 0 dBFS. Demos: https://alejandrozarco.github.io/decorator/ . Free software under the GNU GPL v3, "
           "provided without warranty; not affiliated with or endorsed by any pedal manufacturer.";
  }
  const char* getMaker() const override { return "Decorator"; }
  const char* getHomePage() const override { return "https://github.com/alejandrozarco/decorator"; }
  const char* getLicense() const override { return "GPL-3.0"; }
  uint32_t getVersion() const override { return d_version(0, 1, 0); }

  void initAudioPort(bool input, uint32_t index, AudioPort& port) override
  {
    port.groupId = kPortGroupStereo;
    Plugin::initAudioPort(input, index, port);
  }

  void initParameter(uint32_t index, Parameter& p) override
  {
    p.hints = kParameterIsAutomatable;
    switch (index)
    {
      case kSaturation:
      case kVolume:
        p.name = index == kSaturation ? "Saturation" : "Volume";
        p.symbol = index == kSaturation ? "saturation" : "volume";
        p.unit = "o'clock";
        p.ranges.min = decorator::kKnobMin;
        p.ranges.max = decorator::kKnobMax;
        p.ranges.def = decorator::kKnobDefault;
        {
          // scale points so hosts can show clock positions (7 = 7:00 min, 12 = 12:00, 17 = 5:00 max)
          static ParameterEnumerationValue pts[] = {{7.f, "7:00 (min)"}, {9.f, "9:00"}, {12.f, "12:00"},
                                                    {15.f, "3:00"}, {17.f, "5:00 (max)"}};
          p.enumValues.count = 5;
          p.enumValues.restrictedMode = false;
          p.enumValues.values = pts;
          p.enumValues.deleteLater = false;
        }
        break;
      case kInterfaceDbu:
        p.name = "Interface level";
        p.symbol = "interface_dbu";
        p.unit = "dBu";
        p.ranges.min = decorator::kDbuMin;
        p.ranges.max = decorator::kDbuMax;
        p.ranges.def = decorator::kDbuDefault;
        break;
      case kBypass:
        p.initDesignation(kParameterDesignationBypass);
        break;
    }
    mValues[index] = p.ranges.def;
  }

  float getParameterValue(uint32_t index) const override { return mValues[index]; }
  void setParameterValue(uint32_t index, float value) override { mValues[index] = value; }

  void activate() override
  {
    if (!mEngine.Reset(getSampleRate(), static_cast<int>(getBufferSize())))
      d_stderr2("Decorator: %s", mEngine.Error().c_str());
  }
  void bufferSizeChanged(uint32_t newBufferSize) override
  {
    mEngine.Reset(getSampleRate(), static_cast<int>(newBufferSize));
  }
  void sampleRateChanged(double newSampleRate) override
  {
    mEngine.Reset(newSampleRate, static_cast<int>(getBufferSize()));
  }

  void run(const float** inputs, float** outputs, uint32_t frames) override
  {
    decorator::Params prm;
    prm.saturation = mValues[kSaturation];
    prm.volume = mValues[kVolume];
    prm.interfaceDbu = mValues[kInterfaceDbu];
    prm.bypass = mValues[kBypass] > 0.5f;
    mEngine.Process(inputs, DISTRHO_PLUGIN_NUM_INPUTS, outputs, DISTRHO_PLUGIN_NUM_OUTPUTS, static_cast<int>(frames),
                    prm);
  }

private:
  decorator::Engine mEngine;
  float mValues[kNumParams] = {};

  DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(DecoratorPlugin)
};

Plugin* createPlugin() { return new DecoratorPlugin(); }

END_NAMESPACE_DISTRHO
