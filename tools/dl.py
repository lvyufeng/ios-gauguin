#!/usr/bin/env python3
"""Resumable downloader for this network.

The link here is slow and stalls unpredictably: a transfer can run at 40 KB/s
and then sit at 0 for a minute. curl with --max-time therefore truncates large
files at whatever byte it reached, which silently produced half a header. This
helper resumes instead of restarting and only gives up when the transfer is
*stalled* (no bytes for --stall seconds), retrying a bounded number of times.

  tools/dl.py URL OUT [--stall SECONDS] [--retries N] [--expect-bytes N]
                 [--expect-sha256 HEX]
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time


def size(path):
    return os.path.getsize(path) if os.path.exists(path) else 0


def fetch(url, out, stall=60, retries=8, expect=None, sha=None):
    for attempt in range(1, retries + 1):
        have = size(out)
        if expect and have == expect:
            break
        cmd = ['curl', '-sSL', '--fail', '--connect-timeout', '30',
               '--speed-limit', '1', '--speed-time', str(stall),
               '-C', '-', '-o', out, url]
        started = size(out)
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        got = size(out) - started
        dt = max(time.time() - t0, 1e-6)
        print(f'  attempt {attempt}: +{got}B in {dt:.0f}s '
              f'({got / dt / 1024:.1f} KB/s) total {size(out)}B', flush=True)
        if r.returncode == 0:
            break
        if r.stderr.strip():
            print('   ', r.stderr.strip().splitlines()[-1][:160], flush=True)
        if expect and size(out) == expect:
            break
    if expect and size(out) != expect:
        sys.exit(f'{out}: {size(out)}B, expected {expect}B')
    if sha:
        digest = hashlib.sha256(open(out, 'rb').read()).hexdigest()
        if digest != sha:
            sys.exit(f'{out}: sha256 {digest} != {sha}')
    print(f'{out}: {size(out)}B ok')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('out')
    ap.add_argument('--stall', type=int, default=60)
    ap.add_argument('--retries', type=int, default=8)
    ap.add_argument('--expect-bytes', type=int)
    ap.add_argument('--expect-sha256')
    a = ap.parse_args()
    return fetch(a.url, a.out, a.stall, a.retries, a.expect_bytes,
                 a.expect_sha256)


if __name__ == '__main__':
    sys.exit(main())
