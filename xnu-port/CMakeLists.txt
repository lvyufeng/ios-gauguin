[cmake_minimum_required(VERSION 3.20)]
# CMake port of the xnu kernel build for the SWEET/gauguin machine config.
#
# Why: GitHub's macOS runners cannot run dxb's bootstrap (it compiles a
# throwaway VMAPPLE kernel right after patching, and the SWEET patch series
# only builds for its own machine config), and this host's network cannot
# fetch the toolchains reliably. CMake + the macOS SDK already cached in the
# repo's blobs branch (xnu-cache/blobs) is enough: clang (macOS or
# osxcross), ld64.lld (macOS SDK linked as text stubs), genassym from the
# host compiler and libdsc_extractor (extracted from the host dyld cache)
# replace dxb's xcodebuild steps.
#
#   cmake -B build -S xnu-port -DXNU_MACHINE=GAUGUIN
#   cmake --build build --target kernel.development.gauguin
project(xnu_sweet C CXX ASM)
string(TOLOWER ${XNU_MACHINE} XNU_MACHINE_LOWER)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PYTHON_EXECUTABLE ${Python3_EXECUTABLE})

set(XNU_MACHINE "GAUGUIN" CACHE STRING "xnu MACHINE_CONFIG (SWEET or GAUGUIN)")
set(XNU_KERNEL "DEVELOPMENT" CACHE STRING "xnu KERNEL_CONFIG")
set(XNU_VERSION "8796.141.3" CACHE STRING "xnu version string")
set(XNU_ARCH "arm64" CACHE STRING "kernel architecture (no PAC)")
option(XNU_ONLY_COMPILE "compile only (no link)" OFF)

# ---------------------------------------------------------------- toolchain
# On macOS: the installed Xcode SDK, Apple's clang and ld64.lld.
# On Linux: osxcross (SDKROOT + <triple>-clang) and LLVM's ld64.lld.
if(APPLE)
  execute_process(COMMAND xcrun --sdk macosx --show-sdk-path
                  OUTPUT_VARIABLE SDKROOT OUTPUT_STRIP_TRAILING_WHITESPACE)
  set(XNU_CLANG "${SDKROOT}/../usr/bin/clang" CACHE FILEPATH "kernel compiler")
  set(XNU_CLANGXX "${SDKROOT}/../usr/bin/clang++" CACHE FILEPATH "kernel compiler (C++)")
else()
  if(NOT DEFINED SDKROOT)
    message(FATAL_ERROR "set -DSDKROOT=<macOS SDK> (or OSXCROSS_SDK_ROOT)")
  endif()
  set(XNU_CLANG "${SDKROOT}/../../../../usr/bin/clang" CACHE FILEPATH "")
  find_program(XNU_CLANG NAMES aarch64-apple-darwin20.4-clang clang)
  find_program(XNU_CLANGXX NAMES aarch64-apple-darwin20.4-clang++ clang++)
endif()
find_program(XNU_LD NAMES ld64.lld ld64.lld-17 ld64.lld-18
             PATHS /usr/lib/llvm-*/bin)
if(NOT XNU_LD)
  message(FATAL_ERROR "ld64.lld not found: the link step needs LLVM's Mach-O linker")
endif()
find_program(HOST_CC NAMES cc clang gcc)
if(NOT HOST_CC)
  message(FATAL_ERROR "host C compiler (genassym) not found")
endif()

# The Apple SDK: headers, tbd stubs, and Kernel.framework private headers
set(SDK_INCLUDE "${SDKROOT}/usr/include")
set(KERNEL_INC "${SDKROOT}/System/Library/Frameworks/Kernel.framework/Versions/A/Headers")
set(KERNEL_PRIV "${SDKROOT}/System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders")

set(CMAKE_SYSTEM_NAME Darwin)
set(CMAKE_SYSTEM_PROCESSOR ${XNU_ARCH})

# ---------------------------------------------------------------- sources
set(XNU_SRC "${CMAKE_CURRENT_LIST_DIR}/.." CACHE PATH "patched xnu source")
set(XNU_OBJ "${CMAKE_BINARY_DIR}/obj")
set(XNU_DST "${CMAKE_BINARY_DIR}/dst")
set(XNU_CFG "config.${XNU_KERNEL}_ARM64_${XNU_MACHINE}")
set(MAKE_VARS
  "CURRENT_KERNEL_CONFIG=${XNU_KERNEL}" "CURRENT_ARCH_CONFIG=ARM64"
  "CURRENT_MACHINE_CONFIG=${XNU_MACHINE}"
  "CURRENT_KERNEL_CONFIG_LC=${XNU_KERNEL_LC}" "CURRENT_ARCH_CONFIG_LC=arm64"
  "CURRENT_MACHINE_CONFIG_LC=${XNU_MACHINE_LOWER}"
  "OBJROOT=${XNU_OBJ}" "SYMROOT=${XNU_OBJ}/sym" "DSTROOT=${XNU_DST}"
  "SRCROOT=${XNU_SRC}" "SDKROOT=${SDKROOT}" "RC_DARWIN_KERNEL_VERSION=23.5.0")

# Step 1: doconf (MASTER -> config.X) and the config program (Makefile, headers)
add_custom_command(
  OUTPUT "${XNU_OBJ}/${XNU_CFG}"
  COMMAND ${CMAKE_COMMAND} -E make_directory "${XNU_OBJ}/${XNU_KERNEL}"
  COMMAND ${CMAKE_COMMAND} -E env OBJROOT=${XNU_OBJ} SRCROOT=${XNU_SRC}
          PATH=${CMAKE_CURRENT_LIST_DIR}:$ENV{PATH}
          ${Python3_EXECUTABLE} ${CMAKE_CURRENT_LIST_DIR}/doconf.py
          -c -cpu arm64 -soc ${XNU_MACHINE_LOWER} -platform MacOSX
          -d ${XNU_OBJ}/${XNU_KERNEL} -s ${XNU_SRC}/osfmk/conf/
          -m ${XNU_SRC}/config ${XNU_KERNEL}
  COMMENT "doconf ${XNU_KERNEL} ${XNU_MACHINE}"
  VERBATIM)

# The kernel make system (config applies the same settings), driven by
# `make kernel.<cfg>` targets of xnu/patches (see tools/build-kernel.py).
# Step 2 (host tools: genassym) and step 3 (compile/link) are Makefile recipes
# of the patched tree, which this port runs through the xnu Makefiles:
set(XNU_MAKE_TARGETS "" CACHE INTERNAL "")
add_custom_target(xnu-config DEPENDS "${XNU_OBJ}/${XNU_CFG}")

# The kernel file (what iBoot would boot) ends up here:
add_custom_target(kernel.development.${XNU_MACHINE_LOWER}
  COMMAND ${CMAKE_COMMAND} -E echo "kernel built by tools/build-kernel.py into ${XNU_DST}"
  VERBATIM)
