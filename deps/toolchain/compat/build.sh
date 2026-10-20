#!/bin/bash
# Host-side stand-ins used by deps/build-local.sh.
set -e
here=$(cd "$(dirname "$0")" && pwd)
gcc -O2 -c -o "$here/compat.o" "$here/compat.c" -I "$here"
gcc -O2 -o "$here/installfile" "$here/installfile.c" "$here/compat.o" -I "$here"
ar rcs "$here/libdarwincompat.a" "$here/compat.o" 2>/dev/null || true
echo "built $here/installfile"
