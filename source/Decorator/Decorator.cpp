#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <functional>

#include "../NeuralAmpModelerCore/NAM/get_dsp.h"

#include "Decorator.h"
#include "IPlug_include_in_plug_src.h"
#include "IControls.h"
#include "DecoratorFont.inc"
#include "DecoratorAssets.inc"
#include "nanovg.h"

using namespace iplug;
using namespace igraphics;

namespace
{

void ClockString(double hours, WDL_String& str)
{
  int total = static_cast<int>(std::lround(hours * 60.0));
  int h = (total / 60) % 12;
  int m = total % 60;
  if (h == 0)
    h = 12;
  str.SetFormatted(16, "%d:%02d", h, m);
}

} // namespace

namespace
{
// ---------- pre-rendered UI (scripts/render_ui.py) drawn through NanoVG at native 2x resolution ----------
constexpr float kAssetScale = 2.f; // asset pixels per UI point

// One embedded image (single picture or a grid of animation frames), uploaded once per graphics context.
class Sprite
{
public:
  explicit Sprite(const decorator_assets::Asset& a)
  : mA(a)
  {
  }
  float FrameW() const { return mA.wPx / float(mA.cols) / kAssetScale; }
  float FrameH() const
  {
    const int rows = (mA.frames + mA.cols - 1) / mA.cols;
    return mA.hPx / float(rows) / kAssetScale;
  }
  int Frames() const { return mA.frames; }
  void Draw(IGraphics& g, float cx, float cy, int frame, float alpha = 1.f)
  {
    auto* vg = static_cast<NVGcontext*>(g.GetDrawContext());
    if (!vg)
      return;
    if (mImg <= 0)
      mImg = nvgCreateImageMem(vg, 0, const_cast<unsigned char*>(mA.data), mA.size);
    if (mImg <= 0)
      return;
    frame = std::clamp(frame, 0, mA.frames - 1);
    const float fw = FrameW(), fh = FrameH();
    const float x0 = cx - fw / 2, y0 = cy - fh / 2;
    const float sheetW = mA.wPx / kAssetScale, sheetH = mA.hPx / kAssetScale;
    const NVGpaint paint =
      nvgImagePattern(vg, x0 - (frame % mA.cols) * fw, y0 - (frame / mA.cols) * fh, sheetW, sheetH, 0, mImg, alpha);
    nvgBeginPath(vg);
    nvgRect(vg, x0, y0, fw, fh);
    nvgFillPaint(vg, paint);
    nvgFill(vg);
  }

private:
  const decorator_assets::Asset& mA;
  int mImg = 0;
};

class PedalBackground : public IControl
{
public:
  PedalBackground(const IRECT& bounds)
  : IControl(bounds)
  , mBg(decorator_assets::kBg)
  {
    mIgnoreMouse = true;
  }
  void Draw(IGraphics& g) override { mBg.Draw(g, mRECT.MW(), mRECT.MH(), 0); }

private:
  Sprite mBg;
};

// Filmstrip knob: skirt + pointer rotate (81 pre-lit frames), the spun cap is a static image on top.
class PedalKnob : public IKnobControlBase
{
public:
  PedalKnob(float cx, float cy, int paramIdx, const decorator_assets::Asset& strip, const decorator_assets::Asset& cap)
  : IKnobControlBase(IRECT(cx, cy, cx, cy), paramIdx, EDirection::Vertical, 2.0)
  , mStrip(strip)
  , mCap(cap)
  {
    const float w = mStrip.FrameW(), h = mStrip.FrameH();
    SetTargetAndDrawRECTs(IRECT(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2));
    mRadius = w / 2 / 1.28f; // knob radius (frames include a shadow margin)
  }
  bool IsHit(float x, float y) const override { return std::hypot(x - mRECT.MW(), y - mRECT.MH()) <= mRadius; }
  void OnMouseDblClick(float x, float y, const IMouseMod& mod) override { SetValueToDefault(GetValIdxForPos(x, y)); }
  void Draw(IGraphics& g) override
  {
    const float cx = mRECT.MW(), cy = mRECT.MH();
    mStrip.Draw(g, cx, cy, int(std::lround(GetValue() * (mStrip.Frames() - 1))));
    mCap.Draw(g, cx, cy, 0);
    if (mMouseIsOver || mMouseDown)
    {
      WDL_String str;
      GetParam()->GetDisplay(str);
      const IRECT pill = IRECT(cx - 26, cy - 11, cx + 26, cy + 11);
      g.FillRoundRect(IColor(170, 20, 20, 20), pill, 11.f);
      g.DrawText(IText(14.f, IColor(255, 240, 238, 232), "Montserrat-Bold"), str.Get(), pill);
    }
  }

private:
  Sprite mStrip, mCap;
  float mRadius = 0.f;
};

class BypassLed : public IControl
{
public:
  BypassLed(float cx, float cy, int paramIdx)
  : IControl(IRECT(cx, cy, cx, cy), paramIdx)
  , mLed(decorator_assets::kLed)
  {
    const float w = mLed.FrameW(), h = mLed.FrameH();
    SetTargetAndDrawRECTs(IRECT(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2));
    mIgnoreMouse = true;
  }
  void Draw(IGraphics& g) override { mLed.Draw(g, mRECT.MW(), mRECT.MH(), GetValue() < 0.5 ? 0 : 1); }

private:
  Sprite mLed;
};

// Invisible hit area over the rendered footswitch; click toggles bypass, with a subtle press shade.
class Footswitch : public IControl
{
public:
  Footswitch(const IRECT& bounds, int paramIdx)
  : IControl(bounds, paramIdx)
  {
  }
  bool IsHit(float x, float y) const override { return std::hypot(x - mRECT.MW(), y - mRECT.MH()) <= mRECT.W() / 2; }
  void OnMouseDown(float x, float y, const IMouseMod& mod) override
  {
    mPressed = true;
    SetValue(GetValue() > 0.5 ? 0.0 : 1.0);
    SetDirty(true);
  }
  void OnMouseUp(float x, float y, const IMouseMod& mod) override
  {
    mPressed = false;
    SetDirty(false);
  }
  void Draw(IGraphics& g) override
  {
    if (mPressed)
      g.FillCircle(IColor(50, 0, 0, 0), mRECT.MW(), mRECT.MH(), mRECT.W() * 0.33f);
  }

private:
  bool mPressed = false;
};

constexpr const char* kDemoURL = "https://alejandrozarco.github.io/decorator/";
constexpr const char* kRepoURL = "https://github.com/alejandrozarco/decorator";

// Small text link in the footer; underlines on hover.
class FooterLink : public IControl
{
public:
  FooterLink(const IRECT& bounds, const char* label, std::function<void(IControl*)> onClick)
  : IControl(bounds)
  , mLabel(label)
  {
    SetActionFunction(onClick);
  }
  void Draw(IGraphics& g) override
  {
    const IColor c = mMouseIsOver ? IColor(255, 235, 232, 224) : IColor(255, 160, 158, 152);
    g.DrawText(IText(10.f, c, "Roboto-Regular", EAlign::Far), mLabel.Get(), mRECT);
    if (mMouseIsOver)
    {
      IRECT tr;
      g.MeasureText(IText(10.f, c, "Roboto-Regular", EAlign::Far), mLabel.Get(), tr);
      const float w = tr.W();
      g.DrawLine(c, mRECT.R - w, mRECT.MH() + 6.f, mRECT.R, mRECT.MH() + 6.f);
    }
  }
  void OnMouseDown(float x, float y, const IMouseMod& mod) override
  {
    if (auto f = GetActionFunction())
      f(this);
  }
  void OnMouseOver(float x, float y, const IMouseMod& mod) override
  {
    GetUI()->SetMouseCursor(ECursor::HAND);
    IControl::OnMouseOver(x, y, mod);
  }
  void OnMouseOut() override
  {
    GetUI()->SetMouseCursor();
    IControl::OnMouseOut();
  }

private:
  WDL_String mLabel;
};

// About panel drawn over the pedal: disclaimer, licence, credits, links. Click a button or anywhere else to close.
class AboutPanel : public IControl
{
public:
  AboutPanel(const IRECT& bounds)
  : IControl(bounds)
  {
    Hide(true);
  }
  void Draw(IGraphics& g) override
  {
    g.FillRect(IColor(170, 0, 0, 0), mRECT);
    const IRECT card = Card();
    g.FillRoundRect(IColor(250, 32, 31, 29), card, 10.f);
    g.DrawRoundRect(IColor(255, 70, 68, 64), card, 10.f);
    const IColor ink(255, 236, 233, 226), muted(255, 170, 167, 160);
    float y = card.T + 22.f;
    g.DrawText(IText(17.f, ink, "Montserrat-Bold"), "DECORATOR", IRECT(card.L, y - 10, card.R, y + 10));
    y += 18.f;
    g.DrawText(IText(10.5f, muted, "Roboto-Regular"), "tape saturation  -  version " PLUG_VERSION_STR,
               IRECT(card.L, y - 7, card.R, y + 7));
    y += 22.f;
    for (const char* line : kLines)
    {
      if (line[0] == '\0')
      {
        y += 7.f;
        continue;
      }
      const bool head = line[0] == '#';
      g.DrawText(IText(head ? 11.5f : 10.5f, head ? ink : muted, head ? "Montserrat-Bold" : "Roboto-Regular",
                       EAlign::Near),
                 head ? line + 1 : line, IRECT(card.L + 18.f, y - 7, card.R - 18.f, y + 7));
      y += head ? 17.f : 14.5f;
    }
    DrawButton(g, DemoButton(), "Listen to the demos", true);
    DrawButton(g, RepoButton(), "Source code & full licence", false);
    g.DrawText(IText(10.f, muted, "Roboto-Regular"), "click anywhere to close",
               IRECT(card.L, card.B - 20.f, card.R, card.B - 6.f));
  }
  void OnMouseDown(float x, float y, const IMouseMod& mod) override
  {
    if (DemoButton().Contains(x, y))
      GetUI()->OpenURL(kDemoURL);
    else if (RepoButton().Contains(x, y))
      GetUI()->OpenURL(kRepoURL);
    Hide(true);
    GetUI()->SetAllControlsDirty();
  }

private:
  IRECT Card() const { return mRECT.GetPadded(-14.f).GetVShifted(-4.f); }
  IRECT DemoButton() const
  {
    const IRECT c = Card();
    return IRECT(c.L + 18.f, c.B - 92.f, c.R - 18.f, c.B - 64.f);
  }
  IRECT RepoButton() const
  {
    const IRECT c = Card();
    return IRECT(c.L + 18.f, c.B - 58.f, c.R - 18.f, c.B - 30.f);
  }
  void DrawButton(IGraphics& g, const IRECT& r, const char* label, bool primary)
  {
    g.FillRoundRect(primary ? IColor(255, 196, 52, 34) : IColor(255, 58, 56, 52), r, 6.f);
    g.DrawText(IText(11.5f, IColor(255, 250, 248, 244), "Montserrat-Bold"), label, r);
  }
  static constexpr const char* kLines[] = {
    "#What it is",
    "Ten neural captures of a hardware tape-",
    "saturation pedal, crossfaded by the",
    "Saturation knob. Volume follows the curve",
    "measured on the pedal.",
    "",
    "#Disclaimer",
    "Not affiliated with or endorsed by any",
    "pedal manufacturer. Provided as is,",
    "without any warranty.",
    "",
    "#Licence",
    "Free software under the GNU General Public",
    "License v3. You may use, share and change",
    "it under the terms of that licence.",
    "",
    "#Built with",
    "NeuralAmpModelerCore and AudioDSPTools",
    "(MIT, (c) Steven Atkinson), iPlug2, Eigen",
    "(MPL 2.0), VST3 SDK (MIT). Fonts under the",
    "SIL OFL 1.1 and Apache 2.0 licences.",
  };
};
} // namespace

Decorator::Decorator(const InstanceInfo& info)
: Plugin(info, MakeConfig(kNumParams, kNumPresets))
{
  GetParam(kSaturation)->InitDouble("Saturation", 12.0, 7.0, 17.0, 0.01, "", 0, "", IParam::ShapeLinear(),
                                    IParam::kUnitCustom, [](double v, WDL_String& s) { ClockString(v, s); });
  GetParam(kVolume)->InitDouble("Volume", 12.0, 7.0, 17.0, 0.01, "", 0, "", IParam::ShapeLinear(),
                                IParam::kUnitCustom, [](double v, WDL_String& s) { ClockString(v, s); });
  GetParam(kInterfaceDbu)->InitDouble("Interface level", 12.5, -10.0, 30.0, 0.1, "dBu");
  GetParam(kBypass)->InitBool("Bypass", false);

  mMakeGraphicsFunc = [&]() {
    return MakeGraphics(*this, PLUG_WIDTH, PLUG_HEIGHT, PLUG_FPS, GetScaleForScreen(PLUG_WIDTH, PLUG_HEIGHT));
  };

  mLayoutFunc = [&](IGraphics* pGraphics) {
    pGraphics->AttachCornerResizer(EUIResizerMode::Scale, false);
    pGraphics->LoadFont("Roboto-Regular", ROBOTO_FN);
    pGraphics->LoadFont("Michroma-Regular", MICHROMA_FN);
    pGraphics->LoadFont("Montserrat-Bold", (void*)decorator_fonts::kMontserratBold,
                        int(sizeof(decorator_fonts::kMontserratBold)));
    pGraphics->EnableMouseOver(true);

    const IRECT b = pGraphics->GetBounds();
    const IRECT pedal(20.f, 16.f, 280.f, 726.f); // must match scripts/render_ui.py
    const float cx = pedal.MW();
    pGraphics->AttachControl(new PedalBackground(b));
    pGraphics->AttachControl(new PedalKnob(cx, pedal.T + 129, kSaturation, decorator_assets::kKnobBig, decorator_assets::kCapBig));
    pGraphics->AttachControl(new PedalKnob(cx, pedal.T + 287, kVolume, decorator_assets::kKnobSmall, decorator_assets::kCapSmall));
    pGraphics->AttachControl(new BypassLed(cx, pedal.T + 488, kBypass));
    pGraphics->AttachControl(new Footswitch(IRECT(cx - 48, pedal.T + 549, cx + 48, pedal.T + 645), kBypass));

    // footer: calibration + blend readout
    const IColor muted(255, 140, 140, 136), cream(255, 225, 222, 214), panel(255, 40, 40, 40);
    const IRECT foot(14.f, 734.f, 286.f, 774.f);
    pGraphics->AttachControl(new IVNumberBoxControl(foot.GetFromLeft(118), kInterfaceDbu, nullptr, "Interface dBu",
                                                    DEFAULT_STYLE.WithLabelText(IText(10, muted, "Roboto-Regular"))
                                                      .WithValueText(IText(13, cream, "Roboto-Regular"))
                                                      .WithColor(kFG, panel)
                                                      .WithColor(kFR, muted)
                                                      .WithDrawShadows(false),
                                                    false, 12.5, -10.0, 30.0, "%0.1f", false));
    pGraphics->AttachControl(new ITextControl(foot.GetReducedFromLeft(124).GetVShifted(6), "loading...",
                                              IText(11, muted, "Roboto-Regular", EAlign::Far)),
                             kCtrlTagStatus);

    // footer links + about panel
    auto* about = new AboutPanel(b);
    pGraphics->AttachControl(new FooterLink(IRECT(foot.R - 92.f, foot.T + 1.f, foot.R - 46.f, foot.T + 13.f), "Demos",
                                            [](IControl* c) { c->GetUI()->OpenURL(kDemoURL); }));
    pGraphics->AttachControl(new FooterLink(IRECT(foot.R - 40.f, foot.T + 1.f, foot.R, foot.T + 13.f), "About",
                                            [about](IControl* c) {
                                              about->Hide(false);
                                              c->GetUI()->SetAllControlsDirty();
                                            }));
    pGraphics->AttachControl(about);
  };
}

void Decorator::OnReset()
{
  mEngine.Reset(GetSampleRate(), GetBlockSize());
  SetLatency(decorator::Engine::Latency());
}

decorator::Params Decorator::_Params() const
{
  decorator::Params p;
  p.saturation = GetParam(kSaturation)->Value();
  p.volume = GetParam(kVolume)->Value();
  p.interfaceDbu = GetParam(kInterfaceDbu)->Value();
  p.bypass = GetParam(kBypass)->Bool();
  return p;
}

void Decorator::ProcessBlock(sample** inputs, sample** outputs, int nFrames)
{
  mEngine.Process(inputs, NInChansConnected(), outputs, NOutChansConnected(), nFrames, _Params());
}

void Decorator::OnIdle()
{
  if (auto* ui = GetUI())
  {
    WDL_String s;
    if (!mEngine.Error().empty())
      s.Set(mEngine.Error().c_str());
    else if (!mEngine.Ready())
      s.Set("loading...");
    else
    {
      std::array<double, decorator::kNumCaptures> w;
      decorator::TargetWeights(GetParam(kSaturation)->Value(), w);
      int a = -1, b = -1;
      for (int i = 0; i < decorator::kNumCaptures; i++)
        if (w[i] > 0.001)
        {
          if (a < 0)
            a = i;
          else
            b = i;
        }
      const char* names[] = {"7:00", "8:30", "9:00", "10:00", "11:00", "12:00", "1:00", "2:00", "3:00", "4:00"};
      WDL_String pos;
      ClockString(GetParam(kSaturation)->Value(), pos);
      if (b < 0)
        s.SetFormatted(96, "sat %s: capture %s", pos.Get(), names[a]);
      else
        s.SetFormatted(96, "sat %s: %s %.0f%% + %s %.0f%%", pos.Get(), names[a], 100 * w[a], names[b], 100 * w[b]);
    }
    if (strcmp(s.Get(), mStatus.Get()) != 0)
    {
      mStatus = s;
      if (auto* c = ui->GetControlWithTag(kCtrlTagStatus))
        c->As<ITextControl>()->SetStr(s.Get());
      ui->SetAllControlsDirty();
    }
  }
}
