# Attro core source provenance (`plugins/attro-core`)

Canonical record for Pi **0.85.0** source-core preparation. The attro-core
submodule has no `QUATTRO.md`; this document replaces that role for the root
recipe. Counts and diffs below are **snapshots at the recorded fork pin** and
are not invariant across future pins.

## Pins and identities

| Role | Git commit | Notes |
| --- | --- | --- |
| **Fork pin** (`sources.lock.json` `pin`) | `4cf75e855d51d24cdb6a533bfca4374285566a18` | Reviewed Attro fork tree built during preparation (`ernestjsf/attro-core`). |
| **Upstream base** (`baseCommit`) | `107d79f11072bbc8a3a757ed7fd69596bee7d68c` | Genuine upstream Pi **0.85.0** release commit (may not exist in the fork clone). |
| **Sanitized fork root** (`forkRootCommit`) | `36b02b695383ad89bc3a22b73633be3fa27be3c1` | Local fork history root after sanitization; **not** the upstream base. |

Upstream release tarball (matches `attro.json` `core.source.modelSnapshot` and
`sources.lock.json` `sourceArchive`):

| Field | Value |
| --- | --- |
| URL | `https://github.com/earendil-works/pi/releases/download/v0.85.0/pi-0.85.0-source.tar.gz` |
| SHA-256 | `b4dd5d4db4cd2832389da6445485bbca9db9c6d83bb7504d67975af5c5fe8307` |
| Commit | `107d79f11072bbc8a3a757ed7fd69596bee7d68c` |
| Tree | `f5103239060686ea2983e18906857b3df54428f5` |

Validation uses the **recorded URL and hash** (and descriptor alignment), not
local presence of the upstream git object.

## Fork vs upstream archive diff (pin `4cf75e8`)

Compared **`git archive`** export at pin `4cf75e855d51d24cdb6a533bfca4374285566a18`
against the extracted upstream **0.85.0** release tarball using the **comparison
scope** below (recorded in `sources.lock.json` `forkComparison`; method
`git-archive-pinned-commit-vs-release-archive`):

| Metric | Count |
| --- | ---: |
| Common (fork ∩ archive) | 1658 |
| Identical among common paths | 1588 |
| Content-different among common paths | 70 |
| Fork-only paths | 30 |
| Archive-only paths | 40 |

Fork paths in this comparison scope: **1688** (1658 common + 30 fork-only).
`1588 + 70 = 1658` common paths.

All **40** archive-only paths are **generated provider model data** under
`packages/ai/src/providers/data`. Those paths **are included in archive-only
totals** (not dropped from the comparison). Preparation still applies the
hash-pinned tarball for model data; the fork pin carries Attro-specific source
changes on top of upstream.

### Comparison scope (reproducible)

A path is **in scope** when it is a regular file under the tree root and **none**
of these path segments appear anywhere in the relative path:

- `dist`
- `build`
- `coverage`
- `node_modules`
- `.DS_Store`

Everything else—including `packages/ai/src/providers/data`—participates in
common / fork-only / archive-only counts. Only the five exclusions above are
omitted.

## Change classification (fork pin vs upstream archive)

Rough grouping of the **70** content-different common paths and **30** fork-only paths
(review detail lives in fork history; categories guide release notes):

| Layer | Examples / themes |
| --- | --- |
| **Foundation** | Agent harness and TUI: cancellation semantics, layout/shell integration, shared runtime invariants. |
| **Application** | Interactive product surface: editor behavior, banner/branding hooks, dock sections, profile/consent flows, steering and managed-resource argv. |
| **Temporary compatibility** | `pi-cursor-sdk@0.3.6` loader / npm peer resolution shims until supported upstream loading makes the compatibility shim unnecessary (descriptor npm pin, not submodule). |

## Reproducible verification (no history rewrite)

Safe maintainer workflow to re-check tarball and diff claims:

1. **Download** the release asset (read-only HTTP GET to the URL above).
2. **Verify** SHA-256 matches the table (`shasum -a 256` on macOS, `sha256sum` on Linux).
3. **Extract** to a disposable directory (`tar -xzf`; do not run package lifecycle scripts inside the archive).
4. **Export** the fork with `git archive` at the recorded pin (not a working-tree copy).
5. **Compare** using the commands and snippet below; output must match
   `sources.lock.json` `forkComparison` when pin, tarball, and scope match.
6. **Do not** rewrite git history or mutate the submodule to match upstream; the fork pin is the build input.

Model-data application during preparation is implemented in `attro/core_source.py`
(`apply_model_snapshot`); it enforces the same URL and SHA-256 as the descriptor.

### Exact commands (from repository root)

Replace `/tmp/attrocmp` with any empty disposable directory.

```bash
cd /Users/ernestjusuf/projects/pi-customizations

CMP=/tmp/attrocmp
FORK_PIN=4cf75e855d51d24cdb6a533bfca4374285566a18
URL='https://github.com/earendil-works/pi/releases/download/v0.85.0/pi-0.85.0-source.tar.gz'
EXPECTED_SHA=b4dd5d4db4cd2832389da6445485bbca9db9c6d83bb7504d67975af5c5fe8307

rm -rf "$CMP"
mkdir -p "$CMP"

curl -fL -o "$CMP/pi-0.85.0-source.tar.gz" "$URL"
ACTUAL_SHA=$(shasum -a 256 "$CMP/pi-0.85.0-source.tar.gz" | awk '{print $1}')
test "$ACTUAL_SHA" = "$EXPECTED_SHA"

mkdir "$CMP/archive" "$CMP/fork"
tar -xzf "$CMP/pi-0.85.0-source.tar.gz" -C "$CMP/archive"
git -C plugins/attro-core archive "$FORK_PIN" | tar -x -C "$CMP/fork"

# Upstream tarball unpacks to pi-<version>/; fall back to archive root if layout differs.
if [ -f "$CMP/archive/pi-0.85.0/package.json" ]; then
  ARCH_ROOT="$CMP/archive/pi-0.85.0"
else
  ARCH_ROOT="$CMP/archive"
fi
FORK_ROOT="$CMP/fork"

python3 - "$FORK_ROOT" "$ARCH_ROOT" <<'PY'
import hashlib
import sys
from pathlib import Path

EXCLUDE_SEGMENTS = frozenset({"dist", "build", "coverage", "node_modules", ".DS_Store"})


def in_scope(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    if not path.is_file():
        return False
    return not any(part in EXCLUDE_SEGMENTS for part in rel.parts)


def file_map(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if in_scope(root, path):
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


fork_root, arch_root = map(Path, sys.argv[1:3])
fork_files = file_map(fork_root)
arch_files = file_map(arch_root)
common = set(fork_files) & set(arch_files)
identical = sum(1 for p in common if digest(fork_files[p]) == digest(arch_files[p]))
different = len(common) - identical
fork_only = len(set(fork_files) - set(arch_files))
arch_only = len(set(arch_files) - set(fork_files))
print(f"forkTreePathCount={len(fork_files)}")
print(f"commonPathCount={len(common)}")
print(f"identicalPathCount={identical}")
print(f"differentPathCount={different}")
print(f"forkOnlyPathCount={fork_only}")
print(f"archiveOnlyPathCount={arch_only}")
PY
```

Expected output lines at pin `4cf75e8` with this scope:

```text
forkTreePathCount=1688
commonPathCount=1658
identicalPathCount=1588
differentPathCount=70
forkOnlyPathCount=30
archiveOnlyPathCount=40
```

If output differs, check archive top-level layout (`pi-0.85.0/`), the pinned
`git archive` commit, and that only the five exclusions above were applied.

## Related recipe files

- `attro.json` — `core.source.modelSnapshot` (URL + SHA-256)
- `sources.lock.json` — fork `pin`, `baseCommit`, `forkRootCommit`, `sourceArchive`, `forkComparison`
- `docs/attro-design.md` — release boundaries and source-core build gate
