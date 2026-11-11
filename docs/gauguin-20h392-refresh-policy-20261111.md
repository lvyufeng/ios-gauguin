# Refresh policy in the installed Gauguin iOS build

The HakiOS Renoir report measures a difference between panel refresh and
application frame cadence on iOS 16.5 build 20F66. This inspection follows
the corresponding functions in Gauguin's actual iOS 16 build 20H392. The
input is the verified pre-0240 HFSX backup and its ARM64 shared cache.
[Renoir device report](https://github.com/oosexgang/hakios-xnu-kernel/issues/40).

## Window-server heartbeat

QuartzCore UUID `9e40b2eb260c3af1ae45a1a551a8c1b9` names
`CA::WindowServer::AppleCLCDDisplay::heartbeat_rate()` at unslid
`0x1882dc324`. When the stored interval at object offset `0xb18` is zero,
the function calls `getenv("CA_HEARTBEAT_RATE")`. If the value is present,
it calls `atof` and stores `1 / value` as the initial interval in seconds.
The calls at `0x1882dc348` and `0x1882dc350` resolve through the cache's
branch islands to the matching libsystem_c exports.

Without the environment setting, two existing object fields can supply an
interval. The remaining fallback loads the double `1/60` at `0x18855caa0`.
After the cache field is initialized, a separate conditional return path
can compute an interval from a packed object field at offset `0x230`.
The source of that field and the path taken on the handset remain unknown.
Test any proposed override against measured hardware timing, and measure
the rate actually reported to apps.

The backup contains no `CA_HEARTBEAT_RATE` or `CA_FORCE_TIMER` key in either
the launch cache or the standalone job environment for backboardd and
SpringBoard. Those are the stored launch inputs. Runtime environment and
effective clock source need their own observation. The actual
`CADeviceUseVBL` initialization also reads `CA_FORCE_TIMER`, in a separate
function from the heartbeat. Keep the two controls independent in a test.

## Application opt-in

In the same QuartzCore image, the initialization block for
`CADeviceDisableMinimumFrameDurationOnPhone` reads the main bundle's Info
dictionary. It uses the constant `CADisableMinimumFrameDurationOnPhone`
and passes the result to `CA_CFBoolValue`. The CF calls resolve to
`CFBundleGetMainBundle`, `CFBundleGetInfoDictionary` and
`CFDictionaryGetValue`. Settings, Safari and SpringBoard's actual 20H392
Info.plist files have no explicit opt-in key. This establishes the stored
configuration of those three apps. Effective rates and stock system-app
behavior still need runtime measurement. Apple's documented control for
a custom iPhone app uses the Boolean opt-in and a requested
`CADisplayLink.preferredFrameRateRange`.
[Apple display-link requirements](https://developer.apple.com/documentation/quartzcore/optimizing-iphone-and-ipad-apps-to-support-promotion-displays).

## Hardware acceptance

1. Keep the 0250 correct-desktop trial at its planned 60 Hz software target.
   Confirm the inherited physical scan and latch independently. Recovery's
   measured scan was about 60.24 Hz. It supplies a reference for the recovery
   mode only. [Recovery timing](gauguin-recovery-vblank-20261111.md).
2. After a physical 90 or 120 Hz mode is qualified, run the same bounded app
   workload with the opt-in absent and enabled. Measure
   `UIScreen.maximumFramesPerSecond`, the requested range, callback times and
   target intervals. Compare Settings and SpringBoard separately. If app
   policy or display-clock reporting still needs intervention, test the
   one relevant variable at a time against the same physical mode.
3. Correlate app callbacks with completed compositions, the buffer actually
   latched by scanout, and distinct displayed frames during real gestures.
   Record the first visible response, repeats and missed deadlines. If app
   callbacks speed up while visible frame delivery stays slow, inspect the
   compositor and presentation trace.

## Evidence

DSH stages 82934, 83200 and 83376 each exited zero. They read only the backup
catalog and cache, matched string references to local symbols, resolved the
called functions against export tries, and decoded the fallback constant.
Codex independently checked the three stage receipts, all pins and log
hashes, the exact fallback and all five relevant external call targets.
Raw instructions and local reports are in ignored
`research/tmp/dsh-refresh-policy-0270`. The raw binaries remain in the
original backup. This is static evidence. The effective iOS refresh rate,
physical modes and frame delivery remain pending device qualification.
