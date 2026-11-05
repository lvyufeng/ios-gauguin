#!/bin/bash
# Build the shim on a Mac that has no aarch64-linux-gnu-gcc.
#
#   deps/shim-macos.sh PAYLOAD [--out DIR] [--dtb FILE]
# The optional output directory keeps qualified rollback images intact.
#
# shim/build.sh is written for a Linux cross compiler. On macOS the same
# sources build with Xcode's clang; what differs is only the linker and the
# tools around it, so this script reproduces build.sh step by step:
#
#   * clang -target aarch64-none-elf needs its own freestanding headers, so the
#     compiler's resource directory has to come before any host sysroot (a
#     plain `clang --target=aarch64-none-elf` picks up the macOS libc headers
#     and stops at "unknown type name '__int128_t'" the other way round);
#   * ld64 is the default linker for Arm targets, so ld.lld is forced;
#   * GNU objcopy/readelf/nm are replaced by llvm-objcopy/llvm-readelf/llvm-nm;
#   * clang has no -fno-toplevel-reorder (it is implied) and warns on the GNU
#     flag;
#   * -fno-jump-tables is mandatory, not a style choice: clang turns the
#     switch in exc_handler into a table of string pointers in .rodata, i.e.
#     absolute addresses, which break the "no absolute relocations" rule the
#     shim is linked by (GCC emits a compare chain instead). Without it the
#     link fails with "4 absolute relocations in C objects".
#
# The output image is byte-comparable with the Linux one: the layout is fixed
# by shim.ld and the boot.img v2 header comes from the repo's own packer.
set -euo pipefail
cd "$(dirname "$0")/.."
payload=${1:?usage: deps/shim-macos.sh PAYLOAD [--out DIR] [--dtb FILE]}
shift
OUT=shim/out
DTB=dtb/boot_unpacked/dtb
while [ "$#" -gt 0 ]; do
	case "$1" in
		--out) OUT=${2:?missing --out directory}; shift 2 ;;
		--dtb) DTB=${2:?missing --dtb file}; shift 2 ;;
		*) echo "unknown option: $1" >&2; exit 2 ;;
	esac
done
[ -s "$payload" ] && [ -s "$DTB" ] || { echo "payload/DTB missing or empty" >&2; exit 1; }
LLVM=$({
	if [ -x /opt/homebrew/opt/llvm/bin/clang ]; then echo /opt/homebrew/opt/llvm/bin
	elif [ -x /usr/local/opt/llvm/bin/clang ]; then echo /usr/local/opt/llvm/bin
	else command -v llvm-objcopy >/dev/null && dirname "$(command -v llvm-objcopy)"; fi
}) || { echo "LLVM (llvm-objcopy, ld.lld) is required: brew install llvm lld" >&2; exit 1; }
export PATH=$LLVM:/opt/homebrew/bin:/usr/local/bin:$PATH
CLANG=${CLANG:-clang}
RES=$($CLANG -print-resource-dir)
CFLAGS="-O2 -ffreestanding -nostdlibinc -isystem $RES/include -fno-pic \
	-mgeneral-regs-only -mstrict-align -fno-stack-protector -fno-jump-tables \
	-Wall -Wextra -target aarch64-none-elf"
mkdir -p "$OUT"
for f in start.S shim.c console.c mmu.c fdt.c loader.c pas_reservation.c ufs.c; do
	$CLANG $CFLAGS -c "shim/$f" -o "$OUT/${f%.*}.o"
done
objs="start shim console mmu fdt loader pas_reservation ufs"
# No relocations are resolved by the shim itself: it runs wherever ABL puts it.
# The one allowed exception is start.S's image_size header field, which is the
# linked-at-0 size of _end (build.sh checks the C objects only).
for o in $objs; do
	[ "$o" = start ] && continue
	abs=$(llvm-readelf -r "$OUT/$o.o" | grep -c ABS64 || true)
	[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in $o.o" >&2; exit 1; }
done
$CLANG $CFLAGS -fuse-ld=lld -nostdlib -static -T shim/shim.ld \
	-Wl,--build-id=none -Wl,-N \
	$(for o in $objs; do printf '%s ' "$OUT/$o.o"; done) -o "$OUT/shim.elf"
llvm-objcopy -O binary "$OUT/shim.elf" "$OUT/Image"
# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$(llvm-nm "$OUT/shim.elf" | awk '$3=="_end"{print $1}')
[ -n "$size" ] || { echo "error: _end not found in shim.elf" >&2; exit 1; }
truncate -s "$((16#$size))" "$OUT/Image"
cp "$payload" "$OUT/ramdisk.bin"
python3 tools/mkbootimg2.py "$OUT/shim-boot.img" --kernel "$OUT/Image" --ramdisk "$OUT/ramdisk.bin" \
	--dtb "$DTB" --kernel-offset 0x8000 --ramdisk-offset 0x1000000 \
	--tags-offset 0x100 --dtb-offset 0x1f00000 --page-size 4096 \
	--os-version 17.0.0 --os-patch-level 2035-06 --cmdline "console=null"
python3 tools/unpack_bootv2.py "$OUT/shim-boot.img" "$OUT/check-shim" >/dev/null
cmp "$OUT/check-shim/ramdisk" "$payload" || { echo "error: ramdisk mismatch" >&2; exit 1; }
echo "  payload verified in the image"
ls -l "$OUT/Image" "$OUT/shim-boot.img"
shasum -a 256 "$OUT/shim-boot.img"
