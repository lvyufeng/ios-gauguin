#!/usr/bin/env python3
"""Build the two local Gauguin refresh probe bundles without installing them."""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess


EXECUTABLE = "GauguinRefresh"
OPT_IN = "CADisableMinimumFrameDurationOnPhone"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--simulator", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1] / "userland/refresh_probe.m"
    sdk = "iphonesimulator" if args.simulator else "iphoneos"
    target = "arm64-apple-ios16.0-simulator" if args.simulator else "arm64-apple-ios16.0"
    executable = out / EXECUTABLE
    subprocess.run(["xcrun", "--sdk", sdk, "clang", "-target", target,
                    "-O2", "-Wall", "-Wextra", "-Werror", "-fobjc-arc",
                    "-framework", "UIKit", "-framework", "QuartzCore",
                    "-framework", "Foundation", str(source), "-o", str(executable)], check=True)

    base = {
        "CFBundleIdentifier": "org.gauguin.refreshprobe",
        "CFBundleName": "Gauguin Refresh",
        "CFBundleExecutable": EXECUTABLE,
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1",
        "CFBundleShortVersionString": "1.0",
        "CFBundleSupportedPlatforms": ["iPhoneSimulator" if args.simulator else "iPhoneOS"],
        "LSRequiresIPhoneOS": True,
        "MinimumOSVersion": "16.0",
        "UIDeviceFamily": [1],
        "UILaunchScreen": {},
        "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"],
        "UIApplicationSceneManifest": {
            "UIApplicationSupportsMultipleScenes": False,
            "UISceneConfigurations": {
                "UIWindowSceneSessionRoleApplication": [{
                    "UISceneConfigurationName": "Refresh probe",
                    "UISceneDelegateClassName": "GauguinRefreshScene",
                }],
            },
        },
    }
    bundles = {}
    for name in ("control", "opt-in"):
        app = out / name / (EXECUTABLE + ".app")
        app.mkdir(parents=True)
        path = app / EXECUTABLE
        shutil.copy2(executable, path)
        plist = dict(base, **({OPT_IN: True} if name == "opt-in" else {}))
        info = app / "Info.plist"
        info.write_bytes(plistlib.dumps(plist))
        subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(app)], check=True)
        subprocess.run(["codesign", "--verify", "--strict", str(app)], check=True)
        bundles[name] = {"bundle": str(app), "plist_sha256": sha(info), "signed_binary_sha256": sha(path)}

    result = {"sdk": sdk, "target": target, "source_sha256": sha(source),
              "shared_binary_before_bundle_signing_sha256": sha(executable), "bundles": bundles}
    with (out / "result.json").open("x") as report:
        json.dump(result, report, indent=2)
        report.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
