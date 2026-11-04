#!/bin/bash
# Verify that a packaged boot image really carries the /product properties we
# think it does.
#
# This exists because the same mistake happens twice in this port: build
# something, never boot it, and then not know whether a negative result means
# "the change does nothing" or "the change never shipped". Values lifted from
# Apple's tree also have to be re-encoded little-endian for the ADT, and a
# big-endian copy reads back as a plausible-looking but wrong number.
#
#   tools/check-product-node.sh shim/out/shim-gfx3.img
set -eu
img=${1:?usage: check-product-node.sh IMAGE}
[ -s "$img" ] || { echo "no such image: $img" >&2; exit 1; }

# Properties that must be present inside the packaged image.
want="graphics-featureset-class artwork-device-idiom artwork-scale-factor
      device-perf-memory-class graphics-featureset-fallbacks"
bad=0
for p in $want; do
	n=$(strings -a "$img" | grep -cx "$p" || true)
	if [ "$n" -ge 1 ]; then
		printf '  ok   %s\n' "$p"
	else
		printf '  MISS %s\n' "$p"; bad=$((bad + 1))
	fi
done

# And a couple of neighbours iOS also needs on the same node.
for p in product-name region-info; do
	n=$(strings -a "$img" | grep -cx "$p" || true)
	[ "$n" -ge 1 ] && printf '  ok   %s\n' "$p" || { printf '  MISS %s\n' "$p"; bad=$((bad + 1)); }
done

echo
if [ "$bad" -eq 0 ]; then
	echo "$img: carries every /product property this port publishes"
else
	echo "$img: $bad property name(s) missing - this is not the image you meant" >&2
	exit 1
fi
