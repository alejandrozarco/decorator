
#include <TargetConditionals.h>
#if TARGET_OS_IOS == 1
  #import <UIKit/UIKit.h>
#else
  #import <Cocoa/Cocoa.h>
#endif

#define IPLUG_AUVIEWCONTROLLER IPlugAUViewController_vDecorator
#define IPLUG_AUAUDIOUNIT IPlugAUAudioUnit_vDecorator
#import <DecoratorAU/IPlugAUAudioUnit.h>
#import <DecoratorAU/IPlugAUViewController.h>

//! Project version number for DecoratorAU.
FOUNDATION_EXPORT double DecoratorAUVersionNumber;

//! Project version string for DecoratorAU.
FOUNDATION_EXPORT const unsigned char DecoratorAUVersionString[];

@class IPlugAUViewController_vDecorator;
