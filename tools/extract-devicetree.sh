#!/bin/bash
# Extract a real iPhone device tree from an IPSW.
#
# Apple ships DeviceTree.<board>.im4p: an IM4P wrapper around an LZFSE stream
# (magic "bvx2"). Nothing in the tree could read it until now, which is why the
# port ran for hundreds of rounds on a four-property /product node when the real
# one carries ~130.
#
#   tools/extract-devicetree.sh <ipsw> <board>  e.g. iPhone10,3_...ipsw d22ap
#
# Writes /tmp/<board>.dtb. Needs a C compiler and macOS libcompression.
set -eu
ipsw=${1:?usage: extract-devicetree.sh IPSW BOARD}
board=${2:?usage: extract-devicetree.sh IPSW BOARD}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)

unzip -o -j "$ipsw" "Firmware/all_flash/DeviceTree.$board.im4p" -d "$work" > /dev/null
cc -O2 -o "$work/unlzfse" "$here/unlzfse.c" -lcompression 2>/dev/null || \
	clang -O2 -o "$work/unlzfse" "$here/unlzfse.c" -lcompression

python3 - "$work/DeviceTree.$board.im4p" "$work/payload.lzfse" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read()
i = d.find(b'bvx2')
if i < 0:
    raise SystemExit('no LZFSE payload (bvx2) in the im4p')
open(sys.argv[2], 'wb').write(d[i:])
PY

"$work/unlzfse" "$work/payload.lzfse" "/tmp/$board.dtb"
ls -l "/tmp/$board.dtb"
rm -rf "$work"
