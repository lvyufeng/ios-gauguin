#!/usr/bin/env python3
"""Read a complete kernel build banner; this does not identify an individual boot."""
import argparse
from pathlib import Path
import re

# A binary image contains two identical version strings. Permit duplicate copies,
# reject distinct banners, and require a terminator so truncation is not accepted.
BANNER = re.compile(rb'Darwin Kernel Version [0-9.]+: [^\r\n\x00]+(?=[\r\n\x00])')


def one_banner(data):
    banners = set(BANNER.findall(data))
    if len(banners) != 1:
        raise ValueError(f'expected one complete distinct kernel banner, found {len(banners)}')
    return banners.pop()


def compare(image, log):
    want = one_banner(image.read_bytes())
    have = one_banner(log.read_bytes())
    if want != have:
        raise ValueError('BANNER MISMATCH: log=%r image=%r' % (have, want))
    return want


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    try:
        compare(args.image, args.log)
    except (OSError, ValueError) as error:
        parser.exit(3, f'{error}\n')


if __name__ == '__main__':
    main()
