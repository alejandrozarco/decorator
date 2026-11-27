#pragma once
// DecoratorEngine: the whole Decorator sound, independent of any plugin framework.
// Used by the iPlug2 plugin (macOS/Windows: AU, VST3, app) and the DPF wrapper (Linux VST3/LV2/CLAP).
//
// Ten NAM captures of a tape-saturation pedal, taken at Saturation 7:00 ... 4:00 with Volume at max.
// The Saturation knob crossfades between neighbouring captures; Volume is the measured post-saturation
// gain curve; the interface level (dBu at 0 dBFS) calibrates in/out so the models are driven like the pedal.

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <array>
#include <cmath>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

// The resampler expects two iPlug2 definitions; provide them when building without iPlug2 (DPF wrapper).
#ifdef DECORATOR_NO_IPLUG
namespace iplug
{
static constexpr double PI = 3.14159265358979323846;
}
static constexpr int DEFAULT_BLOCK_SIZE = 1024;
#endif

#include "../AudioDSPTools/dsp/dsp.h"
#include "../AudioDSPTools/dsp/ResamplingContainer/ResamplingContainer.h"
#include "../NeuralAmpModelerCore/NAM/dsp.h"
#include "../NeuralAmpModelerCore/NAM/get_dsp.h"
#include "../NeuralAmpModelerCore/NAM/slimmable.h"

#include "DecoratorModels.inc"

namespace decorator
{
constexpr int kNumCaptures = 10;

// Captures in knob order, with the latency (samples) each trained model adds.
struct Capture
{
  const char* name;
  int latency;
};
constexpr Capture kCaptures[kNumCaptures] = {{"7:00", 21}, {"8:30", 21}, {"9:00", 21},  {"10:00", 22}, {"11:00", 23},
                                             {"12:00", 24}, {"1:00", 24}, {"2:00", 25}, {"3:00", 26},  {"4:00", 26}};
constexpr int kMaxLatency = 26; // the plugin reports this; every path is delayed to match

// Knob anchors: position (clock hours, 7 = min, 17 = max) -> capture. 7:00-8:00 and 4:00-5:00 are dead zones.
struct Anchor
{
  double pos;
  int capture;
};
constexpr Anchor kAnchors[] = {{7.0, 0},  {8.0, 0},  {8.5, 1},  {9.0, 2},  {10.0, 3}, {11.0, 4},
                               {12.0, 5}, {13.0, 6}, {14.0, 7}, {15.0, 8}, {16.0, 9}, {17.0, 9}};
constexpr int kNumAnchors = sizeof(kAnchors) / sizeof(kAnchors[0]);

// Volume curve, dB relative to Volume max (captures were made at max), every quarter hour from 7:00 to 5:00.
// Monotone cubic fit through the measurements at 7, 9, 10:15 (est.), 12, 3 and 5 o'clock.
constexpr double kVolStepHours = 0.25;
constexpr double kVolDb[] = {-26.00, -25.96, -25.83, -25.62, -25.35, -25.01, -24.62, -24.18, -23.70, -22.85, -21.48,
                             -19.84, -18.19, -16.80, -15.64, -14.52, -13.45, -12.43, -11.46, -10.55, -9.70,  -8.88,
                             -8.06,  -7.24,  -6.45,  -5.68,  -4.94,  -4.24,  -3.60,  -3.01,  -2.50,  -2.06,  -1.70,
                             -1.39,  -1.10,  -0.82,  -0.57,  -0.35,  -0.18,  -0.06,  0.00};

// Calibration baked into the captures.
constexpr double kModelInputDbu = 6.1;   // 0 dBFS at the model input
constexpr double kModelOutputDbu = 12.5; // 0 dBFS at the model output

// Parameter ranges shared by all wrappers.
constexpr double kKnobMin = 7.0, kKnobMax = 17.0, kKnobDefault = 12.0;
constexpr double kDbuMin = -10.0, kDbuMax = 30.0, kDbuDefault = 12.5;

// "12:00"-style label for a knob position in hours (7..17).
inline std::string ClockString(double hours)
{
  int m = static_cast<int>(std::lround(hours * 60.0));
  int h = (m / 60) % 12;
  if (h == 0)
    h = 12;
  char buf[16];
  std::snprintf(buf, sizeof(buf), "%d:%02d", h, m % 60);
  return buf;
}

inline void TargetWeights(double knob, std::array<double, kNumCaptures>& w)
{
  w.fill(0.0);
  knob = std::clamp(knob, kAnchors[0].pos, kAnchors[kNumAnchors - 1].pos);
  for (int k = 0; k < kNumAnchors - 1; k++)
  {
    const Anchor& a = kAnchors[k];
    const Anchor& b = kAnchors[k + 1];
    if (knob <= b.pos)
    {
      const double t = (knob - a.pos) / (b.pos - a.pos);
      w[a.capture] += 1.0 - t;
      w[b.capture] += t;
      return;
    }
  }
  w[kAnchors[kNumAnchors - 1].capture] = 1.0;
}

inline double VolumeDb(double knob)
{
  constexpr int n = sizeof(kVolDb) / sizeof(kVolDb[0]);
  const double x = std::clamp((knob - 7.0) / kVolStepHours, 0.0, double(n - 1));
  const int i = std::min(int(x), n - 2);
  const double t = x - i;
  return kVolDb[i] + t * (kVolDb[i + 1] - kVolDb[i]);
}

// Sample rate a NAM model was trained at (old models don't say; they're 48k).
inline double GetNAMSampleRate(const std::unique_ptr<nam::DSP>& model)
{
  const double reported = model->GetExpectedSampleRate();
  return reported <= 0.0 ? 48000.0 : reported;
}

// Runs a NAM model at the host sample rate, resampling when it differs from the model's.
class ResamplingNAM : public nam::DSP
{
public:
  ResamplingNAM(std::unique_ptr<nam::DSP> encapsulated, const double expected_sample_rate)
  : nam::DSP(encapsulated->NumInputChannels(), encapsulated->NumOutputChannels(), expected_sample_rate)
  , mEncapsulated(std::move(encapsulated))
  , mResampler(GetNAMSampleRate(mEncapsulated))
  {
    mBlockProcessFunc = [&](NAM_SAMPLE** input, NAM_SAMPLE** output, int numFrames) {
      mEncapsulated->process(input, output, numFrames);
    };
    if (mEncapsulated->HasLoudness())
      SetLoudness(mEncapsulated->GetLoudness());
    if (mEncapsulated->HasInputLevel())
      SetInputLevel(mEncapsulated->GetInputLevel());
    if (mEncapsulated->HasOutputLevel())
      SetOutputLevel(mEncapsulated->GetOutputLevel());
    Reset(expected_sample_rate, 2048);
  }

  void prewarm() override { mEncapsulated->prewarm(); }

  void process(NAM_SAMPLE** input, NAM_SAMPLE** output, const int num_frames) override
  {
    if (num_frames > mMaxExternalBlockSize)
      throw std::runtime_error("More frames were provided than the max expected!");
    if (!NeedToResample())
      mEncapsulated->process(input, output, num_frames);
    else
      mResampler.ProcessBlock(input, output, num_frames, mBlockProcessFunc);
  }

  int GetLatency() const { return NeedToResample() ? mResampler.GetLatency() : 0; }

  void Reset(const double sampleRate, const int maxBlockSize) override
  {
    mExpectedSampleRate = sampleRate;
    mMaxExternalBlockSize = maxBlockSize;
    mResampler.Reset(sampleRate, maxBlockSize);
    const double upRatio = sampleRate / GetEncapsulatedSampleRate();
    const auto maxEncapsulatedBlockSize = static_cast<int>(std::ceil(static_cast<double>(maxBlockSize) / upRatio));
    mEncapsulated->ResetAndPrewarm(sampleRate, maxEncapsulatedBlockSize);
  }

  double GetEncapsulatedSampleRate() const { return GetNAMSampleRate(mEncapsulated); }

private:
  bool NeedToResample() const { return GetExpectedSampleRate() != GetEncapsulatedSampleRate(); }
  std::unique_ptr<nam::DSP> mEncapsulated;
  dsp::ResamplingContainer<NAM_SAMPLE, 1, 12> mResampler;
  int mMaxExternalBlockSize = 0;
  std::function<void(NAM_SAMPLE**, NAM_SAMPLE**, int)> mBlockProcessFunc;
};

struct Params
{
  double saturation = kKnobDefault; // clock hours 7..17
  double volume = kKnobDefault;     // clock hours 7..17
  double interfaceDbu = kDbuDefault;
  bool bypass = false;
};

class Engine
{
public:
  // Load the embedded captures and size buffers. Returns false (and sets Error()) on failure.
  bool Reset(double sampleRate, int maxBlockSize)
  {
    mReady = false;
    mSampleRate = sampleRate;
    mMaxBlock = std::max(maxBlockSize, 64);
    if (!mModels[0])
    {
      for (int i = 0; i < kNumCaptures; i++)
      {
        try
        {
          const nlohmann::json config = nlohmann::json::parse(decorator_models::kModels[i]);
          std::unique_ptr<nam::DSP> dsp = nam::get_dsp(config);
          if (auto* s = dynamic_cast<nam::SlimmableModel*>(dsp.get()))
            s->SetSlimmableSize(1.0); // full-size A2 network
          mModels[i] = std::make_unique<ResamplingNAM>(std::move(dsp), sampleRate);
          mModels[i]->Reset(sampleRate, mMaxBlock);
        }
        catch (const std::exception& e)
        {
          for (auto& m : mModels)
            m.reset();
          mError = std::string("Capture ") + kCaptures[i].name + " failed to load: " + e.what();
          return false;
        }
      }
    }
    else
      for (auto& m : mModels)
        m->Reset(sampleRate, mMaxBlock);

    mIn.assign(mMaxBlock, 0.0);
    for (int i = 0; i < kNumCaptures; i++)
    {
      mOut[i].assign(mMaxBlock, 0.0);
      mDelayLine[i].assign(kMaxLatency - kCaptures[i].latency + 1, 0.0);
      mDelayPos[i] = 0;
    }
    mDryDelay.assign(kMaxLatency + 1, 0.0);
    mDryPos = 0;
    mFirstBlock = true;
    mError.clear();
    mReady = true;
    return true;
  }

  bool Ready() const { return mReady; }
  const std::string& Error() const { return mError; }
  static constexpr int Latency() { return kMaxLatency; }

  // Mono in (stereo is summed), the same signal to every output channel.
  template <typename T>
  void Process(const T* const* inputs, int nIn, T** outputs, int nOut, int nFrames, const Params& p)
  {
    if (!mReady || nFrames <= 0)
    {
      for (int c = 0; c < nOut; c++)
        for (int s = 0; s < nFrames; s++)
          outputs[c][s] = (nIn > 0 ? inputs[std::min(c, nIn - 1)][s] : T(0));
      return;
    }
    auto monoIn = [&](int i) -> double {
      if (nIn <= 0)
        return 0.0;
      return nIn == 1 ? double(inputs[0][i]) : 0.5 * (double(inputs[0][i]) + double(inputs[1][i]));
    };

    const double inGain = std::pow(10.0, (p.interfaceDbu - kModelInputDbu) / 20.0);
    const double targetOut = std::pow(10.0, (VolumeDb(p.volume) + kModelOutputDbu - p.interfaceDbu) / 20.0);
    std::array<double, kNumCaptures> target;
    TargetWeights(p.saturation, target);
    const double targetBypass = p.bypass ? 1.0 : 0.0;
    if (mFirstBlock)
    {
      mWeight = target;
      mOutGain = targetOut;
      mBypassMix = targetBypass;
      mFirstBlock = false;
    }
    const double smooth = 1.0 - std::exp(-1.0 / (0.02 * mSampleRate)); // ~20 ms

    for (int start = 0; start < nFrames; start += mMaxBlock)
    {
      const int n = std::min(mMaxBlock, nFrames - start);
      for (int s = 0; s < n; s++)
        mIn[s] = static_cast<NAM_SAMPLE>(monoIn(start + s) * inGain);

      // Only run the captures that are (or are about to be) audible: every capture with weight,
      // plus one neighbour on each side so it is already warm when the knob moves onto it.
      std::array<bool, kNumCaptures> active{};
      for (int i = 0; i < kNumCaptures; i++)
        if (target[i] > 1e-6 || mWeight[i] > 1e-6)
          for (int j = std::max(0, i - 1); j <= std::min(kNumCaptures - 1, i + 1); j++)
            active[j] = true;
      for (int i = 0; i < kNumCaptures; i++)
      {
        if (!active[i])
          continue;
        NAM_SAMPLE* in = mIn.data();
        NAM_SAMPLE* out = mOut[i].data();
        mModels[i]->process(&in, &out, n);
        auto& dl = mDelayLine[i]; // equalise latency to kMaxLatency
        const int len = static_cast<int>(dl.size());
        if (len > 1)
          for (int s = 0; s < n; s++)
          {
            dl[mDelayPos[i]] = out[s];
            mDelayPos[i] = (mDelayPos[i] + 1) % len;
            out[s] = dl[mDelayPos[i]];
          }
      }

      for (int s = 0; s < n; s++)
      {
        double y = 0.0;
        for (int i = 0; i < kNumCaptures; i++)
        {
          mWeight[i] += smooth * (target[i] - mWeight[i]);
          if (active[i])
            y += mWeight[i] * mOut[i][s];
        }
        mOutGain += smooth * (targetOut - mOutGain);
        mBypassMix += smooth * (targetBypass - mBypassMix);
        // dry path delayed by the same kMaxLatency as the models, so bypass doesn't shift timing
        mDryDelay[mDryPos] = monoIn(start + s);
        mDryPos = (mDryPos + 1) % int(mDryDelay.size());
        const double dry = mDryDelay[mDryPos];
        y = (1.0 - mBypassMix) * y * mOutGain + mBypassMix * dry;
        for (int c = 0; c < nOut; c++)
          outputs[c][start + s] = static_cast<T>(y);
      }
    }
  }

private:
  std::array<std::unique_ptr<ResamplingNAM>, kNumCaptures> mModels;
  std::atomic<bool> mReady{false};
  std::string mError;
  double mSampleRate = 48000.0;
  int mMaxBlock = 0;
  std::vector<NAM_SAMPLE> mIn;
  std::array<std::vector<NAM_SAMPLE>, kNumCaptures> mOut;
  std::array<std::vector<NAM_SAMPLE>, kNumCaptures> mDelayLine;
  std::array<int, kNumCaptures> mDelayPos{};
  std::array<double, kNumCaptures> mWeight{};
  double mOutGain = 1.0;
  double mBypassMix = 0.0;
  std::vector<double> mDryDelay;
  int mDryPos = 0;
  bool mFirstBlock = true;
};
} // namespace decorator
