// Standalone check of DecoratorEngine: the sample-rate / block-size sequence pluginval uses,
// with parameter changes, printing output RMS. Exits non-zero on any exception or non-finite output.
//   build (clang/gcc): see source/tests/Makefile;  MSVC: see .github/workflows/release-builds.yml
#define DECORATOR_NO_IPLUG
#include <cstdio>
#include <random>
#include "../Decorator/DecoratorEngine.h"

int main()
{
  decorator::Engine e;
  std::mt19937 rng(1);
  std::normal_distribution<double> nd(0.0, 0.03);
  const double rates[] = {44100, 48000, 96000};
  const int blocks[] = {64, 128, 256, 512, 1024};
  int fails = 0;
  for (double sr : rates)
    for (int bs : blocks)
    {
      try
      {
        if (!e.Reset(sr, bs))
        {
          std::printf("reset failed: %s\n", e.Error().c_str());
          return 2;
        }
        std::vector<double> l(bs), r(bs), ol(bs), orr(bs);
        const double* in[2] = {l.data(), r.data()};
        double* out[2] = {ol.data(), orr.data()};
        double acc = 0.0;
        long n = 0;
        bool finite = true;
        for (int b = 0; b < int(sr / bs); b++) // ~1 s
        {
          for (int s = 0; s < bs; s++)
            l[s] = r[s] = nd(rng);
          decorator::Params p;
          p.saturation = 7.0 + 10.0 * (b % 50) / 49.0; // sweep the knob
          p.volume = 12.0;
          e.Process(in, 2, out, 2, bs, p);
          for (int s = 0; s < bs; s++)
          {
            finite = finite && std::isfinite(ol[s]);
            acc += ol[s] * ol[s];
            n++;
          }
        }
        std::printf("sr %6.0f block %5d  rms %7.2f dB  %s\n", sr, bs, 10 * std::log10(acc / n + 1e-30),
                    finite ? "ok" : "NON-FINITE");
        fails += !finite;
      }
      catch (const std::exception& ex)
      {
        std::printf("sr %6.0f block %5d  EXCEPTION: %s\n", sr, bs, ex.what());
        fails++;
      }
    }
  std::printf(fails ? "FAILED\n" : "ALL OK\n");
  return fails ? 1 : 0;
}
