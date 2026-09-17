#!/bin/sh
# Bootstrap Attro from a pinned public release tag into a stable source checkout.
set -eu

ATTRO_REPO_URL="https://github.com/ernestjsf/attro.git"
ATTRO_RELEASE_TAG="v0.2.0-preview.1"
DEFAULT_SOURCE_DIR="${HOME}/.local/share/attro"

err() {
	printf '%s\n' "$*" >&2
}

need_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		err "error: required command not found: $1"
		exit 1
	fi
}

absolute_path() {
	python3 -c '
import sys
from pathlib import Path
value = sys.argv[1]
if not value or "\n" in value or "\r" in value:
    sys.exit("error: installation paths must be nonempty and contain no newlines")
print(Path(value).expanduser().absolute())
' "$1"
}

check_platform() {
	case "$(uname -s)" in
	Darwin) ;;
	Linux) ;;
	MINGW* | MSYS* | CYGWIN*)
		err "error: native Windows is not supported; use WSL2 and run this bootstrap there"
		exit 1
		;;
	*)
		err "error: unsupported platform: $(uname -s)"
		exit 1
		;;
	esac
}

check_python() {
	need_cmd python3
	if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)'; then
		err "error: Python 3.10+ required"
		exit 1
	fi
}

check_node() {
	need_cmd node
	if ! node -e '
const parse = (version) =>
  version.replace(/^v/, "").split(".").map((part) => Number(part));
const current = parse(process.version);
const minimum = [22, 19, 0];
for (let index = 0; index < minimum.length; index += 1) {
  const need = minimum[index] ?? 0;
  const have = current[index] ?? 0;
  if (have > need) process.exit(0);
  if (have < need) process.exit(1);
}
process.exit(0);
'; then
		err "error: Node 22.19.0+ required"
		exit 1
	fi
}

check_prerequisites() {
	check_platform
	check_python
	need_cmd git
	need_cmd npm
	check_node
}

refuse_existing_target() {
	dir=$1
	if [ -L "$dir" ]; then
		err "error: refusing to use symlink path (remove or choose another location): $dir"
		exit 1
	fi
	if [ -e "$dir" ]; then
		err "error: refusing to use existing path: $dir"
		err "Review its contents before resuming an installation, or choose a new ATTRO_SOURCE_DIR."
		err "This bootstrap does not modify or establish trust in an existing checkout."
		exit 1
	fi
}

clone_release() {
	dir=$1
	parent=$(dirname "$dir")
	if [ ! -d "$parent" ]; then
		mkdir -p "$parent"
	fi
	git clone --recurse-submodules --branch "$ATTRO_RELEASE_TAG" "$ATTRO_REPO_URL" "$dir"
}

run_install() {
	dir=$1
	if [ -n "${ATTRO_BIN_DIR:-}" ]; then
		( cd "$dir" && ./install --bin-dir "$ATTRO_BIN_DIR" )
	else
		( cd "$dir" && ./install )
	fi
}

main() {
	check_prerequisites

	source_dir=${ATTRO_SOURCE_DIR:-$DEFAULT_SOURCE_DIR}
	source_dir=$(absolute_path "$source_dir")

	if [ -n "${ATTRO_BIN_DIR:-}" ]; then
		ATTRO_BIN_DIR=$(absolute_path "$ATTRO_BIN_DIR")
		export ATTRO_BIN_DIR
	fi

	refuse_existing_target "$source_dir"
	clone_release "$source_dir"
	run_install "$source_dir"
}

main "$@"
