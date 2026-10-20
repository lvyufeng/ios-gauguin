#!/bin/bash
# BearSSL 7bea48e staging without www.bearssl.org (unreachable from some
# networks): the exact source files are in the blobs branch (deps/mirror).
# Same result as 0020-stage-bearssl.sh + the 0027/0032/0033 wrappers:
# sweet_bearssl/{inc/bearssl_block.h,inc/bearssl_hash.h,
#                src/{inner.h,config.h},
#                src/symcipher/{aes_ct,aes_ct_enc,aes_ct_dec,aes_ct_cbcenc,aes_ct_cbcdec}.c,
#                src/hash/{md5,sha1,sha2big}.c,
#                src/codec/{dec32le,enc32le,dec32be,enc32be,dec64be,enc64be}.c}
set -euo pipefail
cd "${1:?usage: prepare-bearssl.sh XNU_ROOT DEPS_MIRROR}"
mirror=${2:?usage: prepare-bearssl.sh XNU_ROOT DEPS_MIRROR}
[[ -f libkern/crypto/corecrypto_aes.c ]] || { echo >&2 "not an xnu tree"; exit 1; }
[[ -e libkern/crypto/sweet_bearssl ]] && { echo >&2 "refusing to overwrite sweet_bearssl"; exit 1; }
inc=libkern/crypto/sweet_bearssl/inc
src=libkern/crypto/sweet_bearssl/src
mkdir -p "$inc" "$src/symcipher" "$src/hash" "$src/codec"
# bearssl.h is the umbrella that includes the rest of the public headers.
cp "$mirror"/BearSSL/inc/*.h "$inc/"
for f in inner.h config.h; do cp "$mirror/BearSSL/src/$f" "$src/$f"; done
for f in aes_ct aes_ct_enc aes_ct_dec aes_ct_cbcenc aes_ct_cbcdec; do
	cp "$mirror/BearSSL/src/symcipher/$f.c" "$src/symcipher/"
done
for f in md5 sha1 sha2big; do cp "$mirror/BearSSL/src/hash/$f.c" "$src/hash/"; done
for f in dec32le enc32le dec32be enc32be dec64be enc64be; do
	cp "$mirror/BearSSL/src/codec/$f.c" "$src/codec/"
done
echo "Staged BearSSL (6 aes/hash + 6 codec files, $(ls "$mirror"/BearSSL/inc/*.h | wc -l | tr -d ' ') headers) from the mirror"
