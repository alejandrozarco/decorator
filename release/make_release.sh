#!/bin/bash
# Build universal AU/VST3/app and package Decorator-macOS.pkg + Decorator-macOS.zip into release/dist.
# usage: release/make_release.sh VERSION       (run from the repo root, submodules checked out)
set -euo pipefail
V=${1:?version, e.g. 0.1.0}
ROOT=$(cd "$(dirname "$0")/.." && pwd); W="$ROOT/release/work"; D="$ROOT/release/dist"
rm -rf -- "$W" "$D"; mkdir -p "$W"/{vst3,au,app} "$D"
cd "$ROOT/Decorator"
for s in macOS-AUv2 macOS-VST3 macOS-APP; do
  xcodebuild -project projects/Decorator-macOS.xcodeproj -scheme $s -configuration Release \
    ARCHS="arm64 x86_64" ONLY_ACTIVE_ARCH=NO CODE_SIGN_IDENTITY="-" CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM="" \
    VST3_PATH="$W/vst3" AU_PATH="$W/au" APP_PATH="$W/app" SYMROOT="$W/sym" OBJROOT="$W/obj" -quiet
done
P="$W/pkg"; mkdir -p "$P"/{au/Library/Audio/Plug-Ins/Components,vst3/Library/Audio/Plug-Ins/VST3,app/Applications,scripts,out}
ditto "$W/au/Decorator.component" "$P/au/Library/Audio/Plug-Ins/Components/Decorator.component"
ditto "$W/vst3/Decorator.vst3" "$P/vst3/Library/Audio/Plug-Ins/VST3/Decorator.vst3"
ditto "$W/app/Decorator.app" "$P/app/Applications/Decorator.app"
xattr -cr "$P"
printf '#!/bin/sh\n/usr/bin/killall -9 AudioComponentRegistrar >/dev/null 2>&1 || true\nexit 0\n' > "$P/scripts/postinstall"; chmod +x "$P/scripts/postinstall"
for c in au vst3 app; do
  pkgbuild --analyze --root "$P/$c" "$P/$c.plist" >/dev/null
  /usr/libexec/PlistBuddy -c "Add :0:BundleIsRelocatable bool false" -c "Set :0:BundleIsVersionChecked false" "$P/$c.plist"
  args=(--root "$P/$c" --component-plist "$P/$c.plist" --identifier "com.decorator-plugin.pkg.$c" --version "$V" --install-location /)
  [ $c = au ] && args+=(--scripts "$P/scripts")
  pkgbuild "${args[@]}" "$P/out/$c.pkg" >/dev/null
done
sed "s/@VERSION@/$V/g" "$ROOT/release/distribution.xml" > "$P/distribution.xml"
mkdir -p "$P/res"; for f in welcome.html conclusion.html license.txt; do sed "s/@VERSION@/$V/g" "$ROOT/release/$f" > "$P/res/$f"; done
productbuild --distribution "$P/distribution.xml" --resources "$P/res" --package-path "$P/out" "$D/Decorator-macOS.pkg"
Z="$W/zip/Decorator"; mkdir -p "$Z"
for b in "$W/au/Decorator.component" "$W/vst3/Decorator.vst3" "$W/app/Decorator.app"; do ditto "$b" "$Z/$(basename "$b")"; done
sed "s/@VERSION@/$V/g" "$ROOT/release/READ ME - manual install.txt" > "$Z/READ ME - manual install.txt"; xattr -cr "$Z"
(cd "$W/zip" && ditto -c -k --keepParent Decorator "$D/Decorator-macOS.zip")
shasum -a 256 "$D"/*
