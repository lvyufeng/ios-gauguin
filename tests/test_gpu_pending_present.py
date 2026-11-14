#!/usr/bin/env python3
"""Exercise actual frame admission/retry and GPU guards over host object/lock seams.

No XNU VM, board completion, physical scanout or FPS is simulated or claimed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/pending_present_host.cpp"


def method(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]


def unit(tree):
    arm = tree / "iokit/Kernel/arm"
    surface = (arm / "SweetSurface.cpp").read_text()
    header = (arm / "SweetSurface.h").read_text()
    fb = (arm / "SweetFramebuffer.cpp").read_text()
    gpu = (arm / "GauguinGPU.cpp").read_text()
    surface_methods = "\n".join(method(surface, name) for name in [
        "static void\nsweet_surface_put(", "SweetSurface *\nsweet_surface_copy(",
        "SweetSurface *\nsweet_surface_hold(", "void\nsweet_surface_drop("])
    start = fb.index("struct sweet_fb_frame {")
    frame_type = fb[start:fb.index("\n};", start) + 4]
    frame_methods = "\n".join(method(fb, name) for name in [
        "static void\nsweet_fb_frame_release(", "static void\nsweet_fb_frame_move(",
        "static bool\nsweet_fb_frame_prepare(", "static SweetSurface *\nsweet_fb_present_surface(",
        "bool\nAppleCLCD::takeHeldFrameLocked(", "void\nAppleCLCD::cancelHeldFrameLocked(",
        "void\nAppleCLCD::cancelDeferredFrameLocked(", "void\nAppleCLCD::finishHeldFrame(",
        "bool\nAppleCLCD::renderHeldFrame(", "void\nAppleCLCD::removeClient("])
    start = header.index('extern "C" uint32_t GauguinGPUSurfaceBegin(')
    end = header.index("\n};", header.index("class SweetSurfaceGPURead", start)) + 4
    gpu_methods = "\n".join(method(gpu, name) for name in [
        'extern "C" uint32_t GauguinGPUSurfaceBegin(', 'extern "C" void GauguinGPUSurfaceEnd(',
        'extern "C" uint32_t GauguinGPUFrameBegin(', 'extern "C" void GauguinGPUFrameEnd(',
        'extern "C" uint32_t GauguinGPUSurfaceBorrow('])

    # Bind tested helpers to the actual timer, power, close and guarded copy.
    timer = method(fb, "void\nAppleCLCD::vsyncFired(")
    assert "fb->cancelDeferredFrameLocked(&deferred, NULL)" in timer
    assert timer.index("fb->takeHeldFrameLocked(&frame)") < timer.index(
        "fb->renderHeldFrame(&frame,&presented)") < timer.index("fb->finishHeldFrame(&frame,retry)")
    assert "if (rec != NULL && !fb->fDeferGpuPresent) fb->presentClockCopiedLocked();" in timer
    assert "if(fb->fDeferGpuPresent&&presented){\n            ++presents;" in timer
    assert "IOLockLock(fb->fLock);fb->presentClockCopiedLocked();IOLockUnlock(fb->fLock);" in timer
    assert "fDeferGpuPresent=fHoldPresent&&sweet_metal_desktop_enabled()&&gpuAsync==1;" in fb
    present = method(fb, "void\nAppleCLCD::present(")
    assert present.index("SweetSurfaceGPURead gpuRead(s,frameToken)") < present.index("memcpy((void *)(fPixels")
    assert "if(!gpuRead.valid()){s->release();continue;}" in present
    assert "fFB->removeClient(this);" in method(fb, "IOReturn\nIOMobileFramebufferUserClient::clientClose(")

    text = FIXTURE.read_text()
    for key, value in {
        "@SURFACE_METHODS@": surface_methods, "@FRAME_TYPE@": frame_type,
        "@GET32@": method(fb, "static uint32_t\nget32("), "@FRAME_METHODS@": frame_methods,
        "@SWAP_METHOD@": method(fb, "bool\nAppleCLCD::swap("),
        "@GPU_HEADER@": header[start:end], "@GPU_METHODS@": gpu_methods,
    }.items():
        assert text.count(key) == 1, key
        text = text.replace(key, value)
    return "#define HAS_HELD 1\n" + text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, default=os.environ.get("XNU_SOURCE"), required="XNU_SOURCE" not in os.environ)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    tree = args.candidate_root.resolve()
    arm = tree / "iokit/Kernel/arm"
    paths = [Path(__file__), FIXTURE] + [arm / name for name in [
        "SweetSurface.cpp", "SweetSurface.h", "SweetFramebuffer.cpp", "GauguinGPU.cpp", "SweetPresentStats.h"]]
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    with tempfile.TemporaryDirectory(prefix="pending-present-") as directory:
        cpp = Path(directory) / "candidate.cpp"
        cpp.write_text(unit(tree))
        exe = Path(directory) / "candidate"
        subprocess.run([
            "clang++", "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
            "-Wno-unused-function", "-Wno-unused-variable", "-pedantic", "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer", "-I", str(arm), str(cpp), "-pthread", "-o", str(exe),
        ], env=env, check=True)
        result = subprocess.run([str(exe)], env=env, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert pins == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    print(result.stdout, end="")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps({"status": "passed", "inputs": pins, "output": result.stdout,
            "scope": "actual helper bodies; host completion/object/lock/copy seams; no physical FPS"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
