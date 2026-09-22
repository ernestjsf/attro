# Attro core source provenance (`plugins/attro-core`)

Canonical record for Pi **0.87.1** source-core preparation. The attro-core
submodule has no `QUATTRO.md`; this document replaces that role for the root
recipe. Counts and diffs below are **snapshots at the recorded fork pin** and
are not invariant across future pins.

## Pi 0.87.1 integration

Core commit `65885dbf60293ae5b2982bb12f8bbc1e78c125ea` upgrades the prior
Attro fork `e7c1886b8b0831629699e7f10337f8380ac65a8d`. The final recipe pins
`cce2c9d6fe2b7b9e3e58f7cef77e2aa73b5c6e27`, which also includes the approved
Light/Balanced/Deep GPT-6 defaults, and the matching model-data archive below. See
[verification](verification.md#pi-0871-local-candidate) for tested behavior,
review corrections, and platform limits.

The integration uses the verified 0.85.0 and 0.87.1 source archives as the
upstream delta, preserving Attro fork changes without rewriting sanitized Git
history. Generated provider data comes from the new archive, not manual edits.
The accompanying `pi-cursor-sdk` pin is **0.3.10**, which understands Pi's new
transcript-only provider context; `@cursor/sdk` remains **1.0.27** with the
existing attribution-off patch. The user explicitly approved upstream's
`cacheWarming: "streaming"` default, including additional cost-aware provider
requests during active runs. No live profile settings are changed. Independent
review identified warming continuing during cancellation unwind; the candidate
now cancels it synchronously on stop, interruption, and disposal, with scheduled
and in-flight regression coverage.

## Pins and identities

| Role | Git commit | Notes |
| --- | --- | --- |
| **AUDITED SNAPSHOT** (`forkComparison.pin`) | `cce2c9d6fe2b7b9e3e58f7cef77e2aa73b5c6e27` | Frozen commit for archive diff counts below; **not** automatically the current `sources.lock.json` submodule pin after core updates. |
| **Current recipe pin** (`sources.lock.json` `pin`) | (see lock file) | Reviewed Attro fork tree built during preparation (`ernestjsf/attro-core`); may advance when the recipe gitlink updates. |
| **Upstream base** (`baseCommit`) | `f07218c4d4bbc12bef056a7058c3dd49dfe41abe` | Genuine upstream Pi **0.87.1** release commit (may not exist in the fork clone). |
| **Sanitized fork root** (`forkRootCommit`) | `36b02b695383ad89bc3a22b73633be3fa27be3c1` | Local fork history root after sanitization; **not** the upstream base. |

Upstream release tarball (matches `attro.json` `core.source.modelSnapshot` and
`sources.lock.json` `sourceArchive`):

| Field | Value |
| --- | --- |
| URL | `https://github.com/earendil-works/pi/releases/download/v0.87.1/pi-0.87.1-source.tar.gz` |
| SHA-256 | `793949d8d9e56629346e4bb9a6bf5fc17952ef746a1bf4f3185f8e960e806fcf` |
| Commit | `f07218c4d4bbc12bef056a7058c3dd49dfe41abe` |
| Tree | `7053e72909a45c2e400f0506c4aa98e53b26f429` |

Validation uses the **recorded URL and hash** (and descriptor alignment), not
local presence of the upstream git object.

## Fork vs upstream archive diff (pin `cce2c9d`)

Compared **`git archive`** export at pin `cce2c9d6fe2b7b9e3e58f7cef77e2aa73b5c6e27`
against the extracted upstream **0.87.1** release tarball using the **comparison
scope** below (recorded in `sources.lock.json` `forkComparison`; method
`git-archive-pinned-commit-vs-release-archive`):

| Metric | Count |
| --- | ---: |
| Common (fork ∩ archive) | 1861 |
| Identical among common paths | 1763 |
| Content-different among common paths | 98 |
| Fork-only paths | 87 |
| Archive-only paths | 42 |

Fork paths in this comparison scope: **1948** (1861 common + 87 fork-only).
`1763 + 98 = 1861` common paths.

All **42** archive-only paths are **generated provider model data** under
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

Rough grouping of the **98** content-different common paths and **87** fork-only paths
(review detail lives in fork history; categories guide release notes):

| Layer | Examples / themes |
| --- | --- |
| **Foundation** | Agent harness and TUI: cancellation semantics, layout/shell integration, shared runtime invariants. |
| **Application** | Interactive product surface: editor behavior, banner/branding hooks, dock sections, profile/consent flows, steering and managed-resource argv. |
| **Temporary compatibility** | `pi-cursor-sdk@0.3.10` loader / npm peer resolution shims until supported upstream loading makes the compatibility shim unnecessary (descriptor npm pin, not submodule). |

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
FORK_PIN=cce2c9d6fe2b7b9e3e58f7cef77e2aa73b5c6e27
URL='https://github.com/earendil-works/pi/releases/download/v0.87.1/pi-0.87.1-source.tar.gz'
EXPECTED_SHA=793949d8d9e56629346e4bb9a6bf5fc17952ef746a1bf4f3185f8e960e806fcf

rm -rf "$CMP"
mkdir -p "$CMP"

curl -fL -o "$CMP/pi-0.87.1-source.tar.gz" "$URL"
ACTUAL_SHA=$(shasum -a 256 "$CMP/pi-0.87.1-source.tar.gz" | awk '{print $1}')
test "$ACTUAL_SHA" = "$EXPECTED_SHA"

mkdir "$CMP/archive" "$CMP/fork"
tar -xzf "$CMP/pi-0.87.1-source.tar.gz" -C "$CMP/archive"
git -C plugins/attro-core archive "$FORK_PIN" | tar -x -C "$CMP/fork"

# Upstream tarball unpacks to pi-<version>/; fall back to archive root if layout differs.
if [ -f "$CMP/archive/pi-0.87.1/package.json" ]; then
  ARCH_ROOT="$CMP/archive/pi-0.87.1"
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

Expected output lines at pin `cce2c9d` with this scope:

```text
forkTreePathCount=1948
commonPathCount=1861
identicalPathCount=1763
differentPathCount=98
forkOnlyPathCount=87
archiveOnlyPathCount=42
```

If output differs, check archive top-level layout (`pi-0.87.1/`), the pinned
`git archive` commit, and that only the five exclusions above were applied.

## Related recipe files

- `attro.json` — `core.source.modelSnapshot` (URL + SHA-256)
- `sources.lock.json` — fork `pin`, `baseCommit`, `forkRootCommit`, `sourceArchive`, `forkComparison`
- `docs/attro-design.md` — release boundaries and source-core build gate
