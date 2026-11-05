#!/bin/bash
# Source after the pinned dxb function library. No device operations.
# dxb's build_xnu ends with cd and can hide make's error; keep the project
# build explicit, with a fresh installation directory and a checked result.
if [ "${MACOS_VERSION:-}" != 13.5 ]; then
	echo "project series supports only MACOS_VERSION=13.5" >&2
	return 1
fi

get_project_xnu() {
	source "$GITHUB_WORKSPACE/deps/versions.env"
	[ ! -e "$WORK_DIR/xnu" ] || { echo "XNU replay requires a fresh directory" >&2; return 1; }
	git init -q "$WORK_DIR/xnu" || return 1
	git -C "$WORK_DIR/xnu" fetch -q --depth 1 \
		https://github.com/apple-oss-distributions/xnu.git "$XNU_REV" || return 1
	git -C "$WORK_DIR/xnu" checkout -q --detach FETCH_HEAD || return 1
	[ "$(git -C "$WORK_DIR/xnu" rev-parse HEAD)" = "$XNU_REV" ] || return 1
}

apply_project_patches() {
	bash "$GITHUB_WORKSPACE/deps/apply-patches.sh" "$WORK_DIR/xnu" \
		"$GITHUB_WORKSPACE/deps/mirror" gauguin "$WORK_DIR/source-state" || return 1
	# At the pinned dxb revision, CODEQL=1 keeps six tool/path adjustments
	# and bypasses its permissive patch and staging-script loop.
	CODEQL=1 patches
}

build_project_xnu() (
	case "$MACHINE_CONFIG" in gauguin|sweet) ;; *) echo "unsupported machine" >&2; exit 1;; esac
	case "$KERNEL_CONFIG" in DEVELOPMENT|RELEASE|DEBUG) ;; *) echo "unsupported kernel config" >&2; exit 1;; esac
	python3 "$GITHUB_WORKSPACE/tools/xnu-source-state.py" check "$WORK_DIR/xnu" \
		--state-root "$WORK_DIR/source-state" || exit 1
	ensure_hw_env_overrides
	ctf_tool_overrides
	kernel_version_env
	SRCROOT=$WORK_DIR/xnu
	# Keep machines separate, including future multi-machine workflow requests.
	OBJROOT=$BUILD_DIR/xnu-$MACHINE_CONFIG.obj
	SYMROOT=$BUILD_DIR/xnu-$MACHINE_CONFIG.sym
	mkdir -p "$BUILD_DIR/runs" || exit 1
	PROJECT_RUN=$(mktemp -d "$BUILD_DIR/runs/$MACHINE_CONFIG.XXXXXX") || exit 1
	PROJECT_STAGE=$PROJECT_RUN/install
	mkdir "$PROJECT_STAGE" || exit 1
	PROJECT_MANIFEST=$PROJECT_RUN/build-manifest.json
	PROJECT_SDK=$(xcrun --sdk macosx --show-sdk-path) || exit 1
	PROJECT_INPUTS=(--input "versions=$GITHUB_WORKSPACE/deps/versions.env"
		--input "patches=$GITHUB_WORKSPACE/xnu/patches" --input "mirror=$GITHUB_WORKSPACE/deps/mirror"
		--input "project-build=$GITHUB_WORKSPACE/deps/dxb-project.sh" --input "dxb=$WORK_DIR/build.sh"
		--input "generated-sdk=$FAKEROOT_DIR/usr/local" --input "staging-state=$WORK_DIR/source-state"
		--input "generated-frameworks=$FAKEROOT_DIR/System/Library/Frameworks"
		--input "provenance-tool=$GITHUB_WORKSPACE/tools/xnu-build-manifest.py")
	for dependency in bootstrap_cmds dtrace AvailabilityVersions Libsystem libplatform libdispatch; do
		[ ! -d "$WORK_DIR/$dependency" ] || PROJECT_INPUTS+=(--input "$dependency=$WORK_DIR/$dependency")
	done
	export RC_DARWIN_KERNEL_VERSION
	python3 "$GITHUB_WORKSPACE/tools/xnu-build-manifest.py" capture \
		--source "$SRCROOT" --sdk "$PROJECT_SDK" --build-root "$BUILD_DIR" --staging "$PROJECT_STAGE" \
		--output "$PROJECT_MANIFEST" --machine "$MACHINE_CONFIG" --configuration "$KERNEL_CONFIG" \
		"${PROJECT_INPUTS[@]}" || exit 1
	cd "$SRCROOT" || exit 1
	if make install -j8 VERBOSE=YES "${CTF_TOOL_OVERRIDES[@]}" SDKROOT=macosx \
		TARGET_CONFIGS="$KERNEL_CONFIG $ARCH_CONFIG $MACHINE_CONFIG" CONCISE=0 LOGCOLORS=y \
		BUILD_WERROR=0 BUILD_LTO=0 SRCROOT="$SRCROOT" OBJROOT="$OBJROOT" SYMROOT="$SYMROOT" \
		DSTROOT="$PROJECT_STAGE" FAKEROOT_DIR="$FAKEROOT_DIR" KDKROOT="$KDKROOT" \
		TIGHTBEAMC="$TIGHTBEAMC" RC_DARWIN_KERNEL_VERSION="$RC_DARWIN_KERNEL_VERSION" \
		MEMORY_SIZE="$MEMORY_SIZE_OVERRIDE" SYSCTL_HW_PHYSICALCPU="$PHYS_CPU_OVERRIDE" \
		SYSCTL_HW_LOGICALCPU="$LOGICAL_CPU_OVERRIDE" KERNEL_BUILDS_IN_PARALLEL="$KERNEL_PARALLELISM_OVERRIDE"; then
		PROJECT_RC=0
	else
		PROJECT_RC=$?
	fi
	PROJECT_VARIANT=$(echo "$KERNEL_CONFIG" | tr '[:upper:]' '[:lower:]')
	PROJECT_KERNEL=$PROJECT_STAGE/System/Library/Kernels/kernel.$PROJECT_VARIANT.$MACHINE_CONFIG
	python3 "$GITHUB_WORKSPACE/tools/xnu-build-manifest.py" finish --manifest "$PROJECT_MANIFEST" \
		--make-exit "$PROJECT_RC" --kernel "$PROJECT_KERNEL" || exit 1
	mkdir -p "$WORK_DIR/out" || exit 1
	cp "$PROJECT_KERNEL" "$WORK_DIR/out/$(basename "$PROJECT_KERNEL")" || exit 1
	cp "$PROJECT_MANIFEST" "$WORK_DIR/out/build-manifest-$MACHINE_CONFIG.json" || exit 1
)
