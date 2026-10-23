# Obsidian interface

Attro's visual direction is a quiet precision instrument: graphite surfaces,
soft-white text, a single ice-cyan accent, and semantic status colors. Typography,
spacing, and stable layout carry the design rather than decorative animation.

## Appearance

The built-in `obsidian` theme is available in `/settings`. Managed Attro uses it
as the dark fallback when no theme has been selected; explicit user preferences
and the light-terminal fallback remain intact. No personal configuration is
rewritten. To preview it for one invocation after preparing the updated core:

```sh
attro --use-theme obsidian
```

The palette uses `#101216` graphite, `#191D24` surfaces, `#E6EAF0` body text,
`#929CAA` secondary text, and `#78DCE8` accent. Tool failures, warnings, and
successes retain distinct glyphs and labels as well as colors. Syntax uses a
restrained palette instead of making every metadata field compete for attention.

A theme styles component surfaces, not the terminal emulator's entire background
or its font. Set the terminal background to `#101216` for the complete dark
appearance. JetBrains Mono or Berkeley Mono are optional terminal preferences;
Attro does not install fonts or require an icon font.

## Interface principles

- The static, small wordmark leaves space for work. First-run guidance retains
  command discovery, session resumption, and provider setup instructions.
- The composer owns primary activity. Focus, draft text, cursor position, and
  bounded short-terminal layouts take precedence over secondary metadata.
- Assistant prose remains unboxed. User prompts, tool evidence, and decisions
  have distinct treatments without nesting dashboards inside the transcript.
- Tool rows name their action consistently. Failures explicitly say `Failed`
  and retain useful error output while collapsed; full output remains expandable.
- Agent summaries lead with the assignment and execution state. Model, usage,
  cost, and timing are available in details rather than dominating every row.
- Command discovery and session browsing use native keyboard navigation. Browsing
  a conversation must never implicitly branch it or alter model context.
- Decorative startup motion is absent. Working indicators communicate actual
  lifecycle state; no estimated progress percentages are invented.

## Navigation

- `/` shows common commands first, then up to five in-memory recents as you use
  commands. Shortcut hints appear when there is room; Escape dismisses the list
  without deleting the draft.
- `/outline` or Alt+O opens the current conversation's prompts and assistant text
  in fullscreen mode. Enter jumps to a message; Escape keeps the viewport and
  draft unchanged. This is distinct from `/tree`, which can switch branches.
- End or the floating latest-message indicator returns to following output.
  Streaming does not pull the viewport away while you read earlier messages.
- Alt+T and Alt+A focus Tasks and Agents. Escape returns to the draft; disclosure
  state remains independent of focus.

## Development boundary

Core UI changes belong in `plugins/attro-core`, and agent dashboard changes in
`plugins/attro-subagents`. Prepared releases are immutable: source edits do not
change a running installation. Prepare a new release to adopt committed changes;
`/reload` cannot replace the running core. Existing personal themes remain valid.

Rendered verification uses an isolated profile and synthetic session without
provider credentials. This checks the actual terminal layout and keyboard paths,
not provider response quality or platform-wide certification.

## Verification — 2026-10-12

On macOS with Node 26.7.0:

- Core `npm run check` and `npm run build:offline` passed. After the outline
  corrections, `npm run check` and `npm --prefix packages/coding-agent run build`
  passed again, without formatter changes.
- The focused coding-agent run covered 19 files. Three fixture failures from the
  newly assigned Alt+O action and autocomplete dependencies were corrected;
  the final affected editor, status, and tree-navigation run passed all 82 tests.
  The other 16 files retained their passing evidence. Together these cover 223
  tests, including theme loading/export, input geometry, tool rendering, and
  source-text-only outline labels.
- In `packages/tui`, `node --test test/select-list.test.ts test/autocomplete.test.ts
  test/autocomplete-skill-slash.test.ts test/editor.test.ts` passed 237 tests.
  Seven focused fullscreen prompt, manual-scroll, and jump-to-end tests passed.
- The subagents suite passed all 486 assertions against the rebuilt local core.
  An earlier run against stale built dependencies had six RPC fixture failures;
  no runtime fix was needed after rebuilding the dependencies.
- `python3 -m unittest discover -s tests -p 'test_profile_boundary.py' -v`
  passed all 12 profile-boundary tests. Existing user theme choices remain intact.
- Primary LSP diagnostics were clean. Session diagnostics found no blocking
  errors; existing Markdown-link/changelog warnings were outside the UI delta.

The actual compiled CLI ran in a dedicated tmux server with an isolated HOME and
agent directory, environment credentials removed, and the local faux provider.
Inspection covered 40/80/100/120-column layouts, the empty state, slash commands
and recents, tool working/settled/error states, outline Escape/jump, dock focus,
and the real subagent dashboard/detail renderer with synthetic agent records.
The outline was tested through 24→10→24-row resizing. Streaming transcript
captures stayed identical while scrolled back, apart from the separate activity
clock. The small-height selection regression demonstrated red-to-green and was
cleared by independent review.

The checkout already contained unrelated effort-profile removal work. Commits
isolate the UI changes and leave that work unstaged. The profile-preserving
commit candidate also passed `npm run check` and 207 tests across eight focused
UI/profile suites in an exported tree. Its four original profile suites were
unchanged. The committed subagents export also passed all 515 checks against
that profile-preserving core candidate. These additional checks verify the
committed variant rather than assuming that worktree-only evidence covers it. The source-checkout cleanliness
gate (`python3 scripts/verify.py`) remains blocked by those unrelated dirty
submodules; it is not a passing release-certification result. No pre-existing
work was discarded to make that gate green.

Local ANSI captures and fixture scripts are under `/tmp/attro-obsidian-preview`
and `/tmp/attro-obsidian-baseline`; they are development evidence, not shipped
resources. No real provider requests, live-profile edits, pushes, or release
activation were part of this verification.
