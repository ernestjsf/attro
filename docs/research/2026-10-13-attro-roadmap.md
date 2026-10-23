# Attro: a calmer cockpit, a safer agent, a reproducible product

Research roadmap · 13 October 2026 (local; observations began 12 October UTC)

[Open the long visual roadmap](2026-10-13-attro-roadmap.svg)

## Recommendation in one minute

**Do not turn Attro into a collection of every agent plugin. Make the capabilities it already has easier to understand, verify, recover, and maintain.**

My recommended sequence:

1. Establish one authoritative source/release baseline. This checkout targets Pi **0.87.1**, but the installed Attro release is built on **1.0.0** from a different source revision.
2. Improve the existing native composer/dock: attention visibility, keyboard discoverability, constrained-height behavior, and an accessible low-motion presentation.
3. Make “what changed, what was checked, and what is still running” obvious. Keep evidence attached to the exact revision/diff it describes.
4. Pilot **Plannotator** for visual plan/diff review. Add **Context7** only if version-specific documentation retrieval repeatedly saves time. Reuse the existing Chrome DevTools connection before adding another browser tool.
5. Add a deliberate recovery and isolation workflow before increasing unattended autonomy. Session branching, release rollback, worktrees, approvals, and sandboxes solve different problems.
6. Treat public distribution as a separate, gated workstream. Personal productivity does not need to wait for public release, but advertising installation does.

**Best default:** the lean daily-driver path, with the UI-builder add-ons selected per project. Keep multi-agent orchestration and memory as conditional expansions, not mandatory architecture.

Nothing was installed, activated, published, committed, or changed in product/configuration code for this research. The new files are this report and its diagram.

## 1. Scope, evidence, and important distinctions

This is an audit of the current repository, selected installed-release documentation/metadata, and official external documentation. Three read-only research passes covered native UX, distribution/reliability, and the coding-agent landscape. The lead checked package registry metadata and public GitHub availability and synthesized the recommendations.

Other work was changing the checkout during research. In particular, the new [Obsidian interface direction](../design/obsidian-ui.md) appeared before delivery. Treat its graphite/ice-cyan palette, static wordmark, explicit failure labels, and assignment-first agent summaries as ongoing work—not missing features to rebuild. The backlog below targets interaction and verification; reproduce each item against the eventual integrated candidate before implementing it.

### Evidence labels

- **Observed:** read directly in source, manifest, registry, or HTTP response during this research.
- **Recorded:** historical verification or behavior documented by the project; not rerun here.
- **Candidate:** an integration advertised upstream; not tested with Attro.
- **Proposal:** a design recommendation or source-grounded UX hypothesis; not a reproduced runtime defect.

**No current Attro TUI screenshot or authenticated task was exercised.** The wireframes below are proposals, not screenshots. Source inspection alone does not establish clipping, focus, accessibility, performance, or cancellation defects in the live UI. The separate roadmap diagram was rendered for artifact inspection.

### The baseline split is real

| Surface | Observed baseline | Consequence |
| --- | --- | --- |
| Current root checkout | HEAD `2a0623eb702ba5846b688939c03c156595f39f5d`; recipe Attro 0.2.0 / Pi 0.87.1 | This is the repository audited for distribution and native-UI source opportunities. |
| Checked-out core | Gitlink `cd81d9adf61a84fcf32879696670383acfb1c26a`, with substantial pre-existing working changes | Do not mistake dirty source or historical plans for a released feature set. |
| Installed release supplied by this session | `attro-0.2.0-c93e3582ecdc`; manifest and package metadata report Pi **1.0.0**, built from root `31a747430462a0088b4c1033cbda4da6fecef7ac` in a different checkout | Native MCP/codemode features in that artifact cannot simply be assumed to exist in this recipe. |
| Current source direction | Working `docs/using-attro.md` explicitly removes effort profiles, their selector, and suggestions | Do **not** restore those features based on old documentation. Keep explicit `/model`, `/thinking`, and agent definitions. |
| Public availability | Anonymous GitHub API: root public; tags `[]`; releases `[]`; four fork URLs return 404 | Public installation remains unproven. A 404 alone does not prove whether a repository is private or absent; project publication docs identify the forks as private. |

Installed evidence came from the release's `manifest.json`, `pi/packages/coding-agent/package.json`, and relevant docs. No credential or session-history files were inspected. Local machine paths are intentionally abbreviated here.

**Phase-zero decision for future implementation:** select the source line that should produce the next release, preserving the newer installed capabilities and the deliberate simplifications. This research does not authorize a merge, source replacement, history rewrite, or release activation.

## 2. What you already have: retain and expose it

| Capability | Where it exists | Roadmap treatment |
| --- | --- | --- |
| Native composer, primary activity, compact transcript, rich diffs, thinking disclosure | Current core source and [transcript design](../design/transcript-ui.md) | Improve existing ownership. Do not add Zentui/CC renderers alongside it. |
| Todos and recursive subagents, responsive dock, details/steering/cancellation | Managed RPIV/subagent forks and native core dock | Improve coordination visibility and verified lifecycle behavior; no second task engine. |
| LSP navigation, diagnostics, structural/security checks, project/symbol reports | Managed Lens fork | Surface freshness, scope, and actionable results; no duplicate LSP/MCP code-search stack by default. |
| Web research, content fetching, source checking | Managed web-access package and available tools | Keep one research route; add specialized docs only for a demonstrated gap. |
| Structured questions, side questions, keep-awake | ask-user, btw, caffeinate recipe packages | Already covered. Avoid additional modal/question/status extensions. |
| Session resume, branch/fork/clone, compaction, export | Pi foundation; installed session docs | Improve orientation and explanation, not another session store. Conversation branching is not file rollback. |
| Native MCP management, exposure/discovery, allow-once MCP approval | Installed Pi 1.0.0 release docs/source | Configure and carry forward into the aligned recipe; not a new feature to install. |
| Native MCP OAuth keychain storage | Installed managed-release implementation | Retain and verify; do not claim that all provider credentials use this backend. |
| Tool discovery and codemode | Installed release | Reuse deferred discovery and bounded output; another MCP adapter can replace native behavior. |
| Release preparation/activation/status/doctor, shared profile, leases/cleanup | Root manager and [managed state](../../profile/MANAGED.md) | Improve recovery/readiness UX rather than replace the manager. |
| UI-design, commit, handoff, issue-system and orchestration skills | Available personal/session resources | Not automatically bundled for other Attro users. Do not install duplicates or assume a fresh user gets them. |
| Chrome DevTools, Linear, RevenueCat, tldraw | Servers advertised to this session | Availability is not a full health/auth audit. Reuse where relevant; do not activate unrelated business integrations. |

### Avoid these “feature upgrades”

- A second transcript renderer, status spinner, task system, MCP adapter, or subagent runtime.
- Reintroducing effort-profile/team-routing controls that are being removed.
- Automatically switching subscription/API billing routes or models to make an add-on work.
- Installing all skills from a popular collection globally. Each adds routing surface and potentially executable scripts.
- Calling worktrees, project trust, a planning prompt, or `attro try` a sandbox.
- Calling an empty diagnostics cache “the whole project passes.”
- Building a cloud memory service or a new GUI before proving a concrete workflow gap.

## 3. Install / configure / build / defer

### The shortlist

**There are no unconditional “install immediately” recommendations.** First resolve the host baseline; then pilot one addition at a time in disposable state and a disposable workspace. A temporary profile isolates configuration, not host files or credentials.

| Choice | Recommendation | Why / alternative | Compatibility and operating cost |
| --- | --- | --- | --- |
| **Plannotator Pi extension** | **First pilot** for substantial plans and diff review | Annotate plans/messages/diffs in a local browser; structured feedback to the agent. Alternative: Markdown plan + existing ask-user + your editor's diff. | Registry observed `0.28.17`, Pi peer `>=0.79.1`. Both baselines meet the declared minimum, but Attro integration is untested. New UI/process and review state; preserve existing model/thinking and todo ownership. [E1] |
| **Context7** | **Optional docs pilot** | Version-aware library documentation. Compare against current fetch/search on real dependency tasks before keeping it. | Native Pi package observed `0.1.2`, wildcard Pi peer. Choose ONE of native extension, MCP, or CLI+skill. Remote queries/API usage and rate limits apply. Do not send secrets or unnecessary private code. [E2] |
| **Existing Chrome DevTools MCP** | **Reuse/configure** | Screenshots, console/network investigation, performance traces. It is already exposed here. | Use a dedicated browser context. Upstream says usage statistics are on by default and CrUX requests may occur; inspect your actual version/config before opting out. No configuration was changed. [E3] |
| **Playwright CLI** | **Conditional UI-testing addition** | Good for repeatable browser tasks; keep durable tests in the project's existing Playwright suite. Alternative: existing Chrome DevTools for exploratory inspection. | Observed `@playwright/cli@0.1.22`, Node `>=18`. Browser downloads and session state add maintenance. Upstream recommends CLI+skills for coding-agent workflows; token savings are not measured in Attro. [E4] |
| **Playwright MCP** | **Alternative, not another default** | Useful where persistent structured browser interaction is genuinely needed. | Do not run it and Chrome DevTools against one shared authenticated browser unintentionally. Use separate contexts, constrained origins, and narrow task scope. [E4] |
| **Vercel React best-practices skill** | **Project-scoped, React/Next only** | Performance-specific guidance complements your general UI-design skill. It is irrelevant to the native TUI. | Official Vercel repository observed at 32,297 stars; skills.sh page showed 793.4K installs. These are adoption signals, not a security audit. Inspect scripts and pin a reviewed source. [E5] |
| **Whole-process container or VM workflow** | **Prioritize before unattended risky work** | Restrict accessible files, credentials, processes, and network. Alternative for ordinary trusted tasks: existing host workflow with explicit limits. | Integrate a maintained isolation mechanism rather than inventing one. Verify Codex subscription-route compatibility without silently switching to API billing. Tool-only isolation is narrower than whole-process isolation. [E6] |
| **Permission-system extension** | **Evaluate later; not a turnkey safety fix** | Consistent allow/ask/deny may complement native MCP approval. Native approval already covers MCP calls, not arbitrary host activity. | Current `@gotgenes/pi-permission-system@40.2.0` requires Pi/TUI `>=1.0.0`: fails the 0.87.1 recipe requirement, meets installed semver only. README explicitly does not validate fork-host semantics. Its documented in-process subagent integration is not proof for Attro's child-process fork. [E7] |
| **pi-memory** | **Defer until a recall failure is measured** | Start with small reviewed project decisions/handoffs. Add search only if retrieval is a recurring problem. | Observed `0.4.2`, Pi `>=0.81.1`, Node `>=22.19.0`. Core markdown tools work without qmd; semantic search adds qmd, embeddings and indexing. Review project scoping, injection, deletion/restore, and concurrent writes before adoption. [E8] |
| **More GitHub/issue/database MCPs** | **Only for a named project need** | Existing CLI and current Linear/TWG integrations may already cover the job. | Each connection adds credentials, tool exposure, failure states, and possible external writes. Prefer read-only access first; no blanket account scope. |
| **New orchestration dashboard / automatic agent teams** | **Defer** | You already have subagents and external orchestration skills. Improve the existing result and attention loop first. | Multiple coordinators create ownership, budget, and cancellation ambiguity. One orchestrator and one writer per shared seam. |

### Candidate install syntax—not commands executed in this research

After source review, compatibility checks, and a disposable pilot:

```sh
# Choose only the package that solves your observed problem.
attro install npm:@plannotator/pi-extension@0.28.17
attro install npm:@upstash/context7-pi@0.1.2

# Optional personal/project React work, not a TUI dependency.
# Review the source and choose the intended scope in the installer.
npx skills add vercel-labs/agent-skills --skill vercel-react-best-practices
```

These package commands rely on Attro forwarding Pi package-management commands. Verify `attro --help`, the actual core version, and the target profile before using them. Do not run upstream self-update against a managed release. Do not mutate files inside `releases/<id>/`. Managed distribution changes belong in the recipe/locks and require a new prepared release.

A single-invocation `-e` trial can avoid saving a package declaration, but it still loads executable code and may fetch dependencies. It is not a security boundary.

For dotfile changes, inspect the Chezmoi source first, preserve template branches, and apply only the authorized target. No dotfiles were edited here.

### Pilot acceptance gates

**Plannotator:** open/reject/revise/approve a plan; review the actual dirty diff; preserve `/model` and `/thinking`; verify Escape, focus return, restart and cancellation; avoid duplicate todo ownership; inspect plan-mode enforcement across custom tools/codemode/children. Its automatic execution mode must not turn a review-only request into execution. Use external/manual handoff where that matches intent. Upstream's local-first claim has exceptions: release checks, optional remote Git checks, URL fetches, AI actions and sharing can contact services. Disable sharing when inappropriate, and do not equate “local” with “offline.”

**Context7:** compare ten representative documentation questions against current web tools. Record correct version match, citation quality, latency, request volume, and whether private content was sent. Keep it only if the retrieval benefit exceeds added configuration/tool ambiguity. Wildcard peer compatibility is not a test result.

**Browser tooling:** run the project's existing task at desktop and narrow viewport, capture console errors, check keyboard flow, and verify a clean profile contains no unrelated cookies. Persist useful regression checks in the project, not only in an agent transcript.

**Permissions/isolation:** nested tool calls, child agents, shell wrappers, symlink paths, denied operations, disconnected approval UI, cancellation and concurrent requests must obey the same intended policy. Policy gates and OS containment need separate tests and independent sensitive-change review.

## 4. What to borrow from other agents—and what not to copy

Official docs were consulted; this is not a comparative benchmark.

| Reference | Useful pattern | Attro adaptation | Avoid |
| --- | --- | --- | --- |
| **Claude Code** | Explicit permissions, sandbox guidance, checkpoint/rewind UX | Name the scope of every recovery action and approval. Make “conversation” vs “files” unmistakable. | Claiming checkpoints reverse all shell commands or external effects. [E9] |
| **Codex CLI** | Separate approval and sandbox controls | Show the actual execution boundary and current route; keep network scope visible for autonomous tasks. | Calling an approval dialog isolation, or bypassing the chosen subscription route. [E10] |
| **OpenCode** | Read-only planning agent and allow/ask/deny policy vocabulary | Clear “inspect” vs “execute” intent with explicit enforcement scope. | A second model/profile routing layer merely to expose plan mode. [E11] |
| **Aider** | Git-aware workflow and explicit lint/test commands | Reuse project-owned checks and show exact results against a diff. | Automatic commits or tests that override user/project policy. [E12] |
| **Gemini CLI** | Pre-modification snapshots and restore UX | Adopt an explicit checkpoint inventory and explain untracked/external-effect limits. | Treating snapshotting as universal recovery. [E13] |
| **Pi** | Small core plus skills/extensions/packages and session trees | Build essential interaction contracts into core; keep optional integrations modular and pinned. | Reimplementing native sessions/MCP or creating a permanently larger system prompt. [E14] |

The differentiator should be **a trustworthy terminal control surface**, not the longest feature checklist.

## 5. UI/UX direction

Preserve the existing visual language and ongoing Obsidian direction: unboxed transcript, native composer, subdued separators, semantic theme colors, compact dock. Do not rebuild the screen as a dashboard of competing cards. The cream/green/blue roadmap illustration is a document visualization, not a proposed replacement application theme.

### Three levels of information

1. **Always visible:** editable draft, actual execution state, urgent decision/denial, queued-input count, and a compact project identity.
2. **One action away:** active tasks/agents, changed files, verification evidence, route/model details, context provenance, full error.
3. **On demand:** historical agents, complete tool output, deep diagnostics, raw metadata, release inventories.

Use one accent for the active interaction and semantic warning/error colors for real conditions. Do not color ordinary prose as if it were an alert. Preserve per-message reasoning disclosure; do not make raw reasoning the primary progress feed.

### Wide terminal concept (proposal)

```text
  Attro · project / branch                           session: repair parser

  Findings and useful commentary remain in chronological order.
  ✓ Read parser.ts:42–76       3-line preview · expand for full evidence
  ! Check failed              exact command · exit 1 · open output

  ── Needs input: approve external write ────────────────────────────────
     scope / actor / destination                         [inspect] [deny]
  ── Queue: 1 steering · 1 follow-up ────────────────────────────────────
  > Editable draft stays here; no modal steals it for routine updates.
  ── Codex route · selected model · high      context: 42% / current ─────
  ▸ Tasks 2/5     ▸ Agents 1 running / 1 unread     ▸ Checks 1 failed
  project / branch · dirty 3 files                         [? shortcuts]
```

This rearrangement is conceptual; preserve the incumbent composer placement unless renders demonstrate a reason to change it. “Unread” and a consolidated Checks surface are proposed capabilities, not claims about current implementation. Do not show both a new Checks summary and a redundant Lens Diagnostics summary; choose one integration contract.

### Narrow / short terminal concept (proposal)

```text
  ...transcript...
  ! Needs approval · inspect / deny
  Queue 2 · one steering
  > draft remains editable
  Codex · high · ctx 42%
  Tasks 2/5 | Agents 1 | Check failed
```

At reduced height, remove decorative detail before hiding attention or queue state. Keep a command-based fallback when there is not enough space to show lists. A short terminal should become less detailed, not less controllable.

### Ranked UX backlog

Paths below use **C = `plugins/attro-core/packages/coding-agent/src/modes/interactive/`**. Line references describe the audited working tree and may shift. All runtime issues in this table are **hypotheses/proposals**, not reproduced defects. First port the investigation to the agreed Pi 1.0 baseline where applicable.

| ID / priority | Change or investigation | Evidence and reason | Acceptance / variation |
| --- | --- | --- | --- |
| **UX01 / P1** | Keep a queued-message count/action visible under vertical pressure | `C/chat-viewport.ts:68–94` can trim pending-message rows to zero; `components/queued-messages.ts:27–65` owns the fuller preview | At 80×24 and 60×16, queued/applying/stopped remain distinguishable. Smallest fix: count in the composer, not a new queue pane. |
| **UX02 / P1** | Define attention precedence | `components/primary-activity.ts:103–148,219–258`; queue/dock state exists separately | Exercise retry + child failure + queued input + stop. Show the blocking action without claiming idle/success; retain background state. |
| **UX03 / P1** | Publish a discoverable focus/shortcut map | `components/dock-sections.ts:182–210`; [current dock controls](../design/transcript-ui.md) | Hints derive from configured bindings; repeated focus shortcut returns to the draft; modal and editor bindings do not collide. Prefer contextual hints over more shortcuts. |
| **UX04 / P1** | Validate constrained-height list access | `C/chat-viewport.ts:74–109`; `components/dock-sections.ts:358–423` | Expanded lists have useful rows where possible; details remain reachable by commands when not. Preserve draft/caret/undo across resize. |
| **UX05 / P1** | Strengthen non-color focus/attention cues | `components/attro-editor.ts:45–47,109–111`; dock selected-row styles | Theme and monochrome checks distinguish focused editor, selected item and failure. Text/glyph plus styling; do not rely on faintness alone. |
| **UX06 / P1** | Verify IME, Unicode and paste across focus changes | `C/interactive-mode.ts:665–668`; editor resizing at `chat-viewport.ts:95–118` | CJK composition follows caret; emoji/combining characters wrap correctly; multiline/bracketed paste survives dock navigation. Fix only reproduced failures. |
| **UX07 / P1** | Add explicit verification freshness | Existing Lens diagnostics and task completion are different sources of truth | Display command/scope/revision or diff fingerprint/time and `pass/fail/stale/not run`. Never turn historical green into current green. Integrate, don't duplicate Lens. |
| **UX08 / P1** | Make recovery-oriented errors | Dock action handlers at `components/dock-sections.ts:281–316`; retry/stop states already exist | One error + what failed + next action; retain input. “Retry connection” is distinct from replaying a possibly completed write. |
| **UX09 / P2** | Improve queue inspection/editing | `components/queued-messages.ts:44–64` displays three compact previews; existing dequeue restores messages | Mixed steering/follow-up entries retain type/count and full-text recovery. Reuse dequeue before designing reorder/delete machinery. |
| **UX10 / P2** | Prioritize child results requiring attention | Existing responsive agents/history and completion notifications | Textual failed/waiting/unread summary; inspect exact child and acknowledge result without stealing focus. Parent final answer is not “all children done.” |
| **UX11 / P2** | Make context usage provenance explicit | `components/attro-editor.ts:146–153,230–268`; metadata refresh in interactive mode | Current vs estimated/unknown after compaction, model switch and resume; show expensive context contributors on demand. Keep existing `/context`. |
| **UX12 / P2** | Add one changed-files/review entry point | Rich diffs already exist per tool; a task-level view is a separate proposed seam | Distinguish pre-existing user changes from task changes; staged/untracked/binary states explicit. Link to existing diff viewer or Plannotator before building another editor. |
| **UX13 / P2** | Audit truncated and failed transcript output | `components/assistant-message.ts:211–232`; `compact-tool-render.ts:37–123` | Failure and source truncation survive collapse; keyboard reveals full output; narrow labels retain action and useful target. |
| **UX14 / P2** | Low-motion / simple-output presentation | Activity animation exists; theme support alone is not accessibility | Optional static status, slower/coalesced updates, ASCII-safe fallback. Evaluate real screen-reader + terminal combinations; do not claim WCAG conformance from a TUI code audit. |
| **UX15 / P2** | Rationalize settings discoverability | Native transcript prefs remain JSON; `/ccstyle` was intentionally removed | Put the few supported high-value preferences in existing settings/help, explain scope and restart/reload requirement. Do not restore a retired renderer control panel. |
| **UX16 / P2** | Expose execution route and budget truth | Model/thinking and usage already have surfaces; subscription billing differs from API pricing | Show provider/route and known usage without invented dollars. Unknown price is “unknown,” not zero. Children and cache-warming count toward request visibility. |
| **UX17 / P2** | Consolidated capability/health inspection | Installed `/mcp`, `/session`, Lens, doctor already exist | A navigational index links existing detail views: loaded/skipped/failed, source scope, version and reason. Avoid a second configuration database. |
| **UX18 / P3** | Session recovery/orientation polish | Pi already saves, names, searches and branches sessions | Explain cwd, branch, draft and what resume restores. Preview any filesystem recovery separately. Improve labels before building a session manager. |
| **UX19 / P3** | Accessible artifact handoff | Exports, fetched assets and diagrams are distributed across tool output | Stable local artifact links, type, origin and privacy status. Sharing is explicit and never automatic. |
| **UX20 / P3** | Validate extension fallback contracts | `C/interactive-shell.ts:137–180`; `chat-viewport.ts:134–165` | Custom editors and unsupported hosts have documented fallbacks; native activity remains single-owner. Do not assume every extension understands the dock. |

### State matrix for UX verification

Use representative scenarios, not an enormous new testing framework:

- **Empty/startup:** no login, no model, no tasks, unavailable extension, untrusted project.
- **Active:** streaming text, long tool, multi-line draft, simultaneous child results, queued steering/follow-up.
- **Attention:** denied permission, expired login, disconnected MCP, failed check, partial/truncated output.
- **Lifecycle:** stop while a tool is active, cancel a child, retry a transient read, resume after crash, compact, change model, branch session.
- **Layout:** 120×40, 80×24, 60×16, a 40-column stress case, live resize, dark/light/low-contrast themes, keyboard-only, mouse selection, IME.

Preserve existing behavior first. For confirmed regressions, extend the smallest existing behavioral test at a public seam. Use real isolated PTY captures for layout/focus. Browser screenshots validate browser integrations, not the terminal UI. WCAG web guidance is useful for browser surfaces; terminal accessibility requires terminal-specific evidence. Nonessential interaction animation is covered by WCAG 2.3.3 at AAA, not an automatic AA claim. [E15]

## 6. The long roadmap

**Estimates are planning ranges for one experienced maintainer, not promises or measured velocity.** Each phase has an exit gate; move by evidence, not calendar. External publication clearance can dominate elapsed time. Optional branches need not all be completed.

### Phase 0 — Make the baseline truthful (roughly 2–5 focused days, excluding merge surprises)

**Outcome:** everyone knows which source builds the next release.

- **R00:** record recipe/core/plugin pins, installed provenance, effective capabilities, and the intended source line.
- Reconcile historical docs with current behavior; preserve effort-profile removal.
- Produce a compatibility matrix for the actual Pi 1.0/custom fork and optional packages.
- Carry current MCP, discovery and keychain capabilities forward rather than reinstall replacements.
- Separate “implemented,” “tested on this revision,” and “publicly available.”

**Gate:** a clean candidate's version, provenance, managed resources and advertised feature inventory agree. No fabricated pins or weakened dirty-tree checks.

**Owners:** root manager/release recipe + core maintainer. **Alternative:** retain the current private daily-driver artifact while preparing a clean source candidate; do not downgrade the live installation merely to match this checkout.

### Phase 1 — Make the everyday cockpit obvious (1–2 weeks)

**Outcome:** fewer hidden states and less interruption.

- UX01–06: constrained queue visibility, attention precedence, focus/shortcut guidance, small-terminal access, non-color cues and input integrity.
- Render existing UI before changing it. Preserve single activity ownership and chronological transcript.
- Add a small interaction/help index, not a separate dashboard.
- Surface model/route/default-setting scope clearly without resurrecting profiles.

**Gate:** keyboard-only and resize scenarios preserve draft/caret/undo; waiting/stopped/error states are distinguishable; critical controls remain reachable.

**Alternative A:** docs/hints and targeted fixes only. **Alternative B:** modest native layout refinement after rendered evidence. Do not introduce new display plugins for either.

### Phase 2 — Make progress and verification inspectable (1–2 weeks)

**Outcome:** “done” comes with inspectable evidence, not just a confident answer.

- UX07,10–13: verification freshness, child-result attention, context provenance, task-level changed-files link.
- Record exact check, exit status, scope and source fingerprint; invalidate affected evidence on relevant edits.
- Use existing project commands and Lens; respect “no new tests unless requested/required.”
- Pilot Plannotator, or keep the terminal/editor review route if it is faster.
- Completion summary distinguishes implementation, checks, unverified limits and running children.

**Gate:** a check can be failed, passed, stale or not run; opening it reveals actual evidence. Pre-existing user edits are not attributed to the agent.

**Alternative:** first ship a structured final-summary convention and local review link. Build a persistent native review surface only if this proves insufficient.

### Phase 3 — Make autonomy recoverable and bounded (2–4 weeks, security-sensitive)

**Outcome:** a user knows what can be affected and how to recover what is recoverable.

- **R03a:** documented snapshot/backup workflow for workspaces and profile state; restore preview before writes.
- Distinguish session rewind, file checkpoint, Git revert, release rollback and profile restore.
- **R03b:** tested whole-process container/VM reference workflow with minimal mounts and explicit network/credential exposure.
- **R03c:** optional policy integration; native MCP approvals remain the baseline for MCP.
- **R03d:** budgets for elapsed time, concurrent agents, request/turn counts, and observable cost; stop cleanly and report unfinished work.
- Keep existing concurrency limits until measurements justify changing them.

**Gate:** failure-path tests cover dirty/untracked files, interrupted restore, active processes, denied nested calls and cancellation. Independent review is mandatory before changing auth, persistence, destructive recovery or concurrency semantics.

**Alternative A:** docs + manual snapshots + existing isolation tools. **Alternative B:** native checkpoint UX. The latter is substantially more expensive and should follow proven demand, not precede it.

### Phase 4 — Add only workflow-specific intelligence (1–3 weeks across selected pilots)

**Outcome:** fewer incorrect library/API choices and reproducible UI validation without tool clutter.

- Context7 if the ten-task pilot beats existing research tools.
- Playwright CLI for repeatable UI tasks; Chrome DevTools remains exploratory inspection/performance.
- Project-scoped React skill where relevant; reuse existing UI-design instructions.
- Integration cards disclose source, version, permission/data boundary, cost, health and removal route.
- Keep deferred tool exposure; measure startup/context costs before enabling tools broadly.

**Gate:** each installed addition solves a named gap, has a pinned source and owner, passes a smoke check, and has a clean disable/remove path.

**Alternative:** zero new installs. Configure existing tools and keep all special-purpose capabilities project-local.

### Phase 5 — Scale coordination only where it pays (2–4 weeks, optional)

**Outcome:** agents produce useful independent work without hidden cost or conflicting writes.

- Improve existing subagent lifecycle/result UX before adding orchestration abstractions.
- Explicit objective, paths, known facts, acceptance, forbidden scope and report contract per task.
- One writer per file/shared seam; independent work only in parallel.
- Optional isolated workspaces/worktrees with reviewed integration, no automatic discard.
- Per-child route/budget/heartbeat/cancel state and a result inbox; no success from silence.
- If memory is needed, start with reviewed decisions and provenance, then evaluate local search.

**Gate:** benchmark representative sequential vs parallel tasks using wall time, total tokens, accepted changes and review burden. Parallelism must beat the simpler baseline without worse failure recovery.

**Alternative:** one lead plus occasional read-only reviewer. That is a valid permanent stopping point, not an incomplete product.

### Phase 6 — Deliver a credible public preview (2–6+ weeks; parallel release lane)

**Outcome:** a stranger can safely obtain and run the documented product.

- Complete publication/history/retained-data clearance and license/dependency inventory.
- Prove anonymous retrieval of every pinned fork/ref. Do not expose private histories as a shortcut.
- Clean macOS/Linux install and supported runtime-floor checks; treat WSL2 as a separate evidence decision.
- Tagged bootstrap, first launch/login, bounded authenticated task, model-driven nested task, update/profile continuity and recovery drill.
- Explain the two moving parts: launcher/manager source checkout and activated core/plugin release.
- Keep rollback availability honest; previous release code may already be pruned.
- Publish a reviewed preview only after evidence; no implicit stable feed.

**Gate:** public source retrieval + actual clean install + tested recovery + accurate docs. Historical local-object installs are valuable but cannot satisfy anonymous delivery.

**Alternative A:** remain an excellent private workbench. **Alternative B:** reviewed source-built preview. **Alternative C, later:** signed prebuilt artifacts after there is adoption and a maintainer willing to own packaging/provenance.

### Phase 7 — Invest based on repeated friction (3–6 month horizon, not committed scope)

Choose at most one substantial bet at a time:

- **Portable packaging:** relocatable launcher or signed binaries if source-install friction dominates.
- **Session/artifact workbench:** better local retrieval and review if long projects repeatedly lose context.
- **Team policy distribution:** versioned, inspectable policy with explicit local/project precedence if multiple users need it.
- **Reviewed update PR automation:** extend discovery to tested PRs; clean merges never equal release approval.
- **Optional GUI companion:** only if terminal-native review remains a repeated blocker after trying existing review tools.
- **Local memory search:** only if small project records and existing session navigation fail a measured recall task.

**Gate:** named user problem, baseline, success metric, owner, cost ceiling and removal plan. “Competitor has it” is not sufficient.

## 7. Four variations you can actually choose

| Path | Choose when | Sequence | Install policy | Stop condition |
| --- | --- | --- | --- | --- |
| **A · Lean daily driver — recommended** | Most work is coding/research in trusted projects | 0 → 1 → 2; manual recovery from 3 | Existing stack; optional Plannotator only | Reliable input/attention, inspectable changes/checks, low maintenance |
| **B · UI builder** | Frequent frontend implementation and visual QA | A + selected 4 | Existing DevTools; Playwright CLI if repeatable flows; React skill per project; optional Context7 | Before/after evidence and existing project tests cover actual UI changes |
| **C · Bounded autonomous workshop** | Long-running tasks and useful independent subtasks | 0 → 1 → 2 → 3 → 5 | Isolation/policy pilots; no competing orchestrators | Enforced scope, meaningful budgets, reliable stop/recovery and better measured throughput |
| **D · Public Attro product** | Supporting users beyond the maintainer | 0 + release lane 6 alongside 1/2; selected 7 later | Small supported compatibility set | Credential-free public install, platform gates, recovery and sustainable updates |

**Important:** these are roadmap/workflow variations, not a proposal to recreate effort profiles, add runtime routing presets, or maintain four product distributions. Start with one recipe and document optional workflows.

### Trade-off decisions for future implementation

| Decision | Default recommendation | Choose the alternative when |
| --- | --- | --- |
| Native core vs extension | Core for input, focus, activity ownership and common status; extension for optional domain integrations | A capability can be removed without breaking the common interaction model |
| Terminal review vs browser review | Native summaries + existing editor; pilot browser annotations | Plans/diffs require enough discussion that a separate review surface saves time |
| Context7 extension vs MCP vs CLI | Select one after benchmark; native integration may be simplest, existing MCP visibility may be clearer | CLI is preferable for occasional tasks; MCP for managed shared connections; don't enable all three |
| Sandbox whole process vs tools only | Whole process for strong containment expectations | Tool-only VM is a deliberate narrower boundary and all escape-capable tools are enumerated |
| Manual backup vs native checkpoints | Manual recovery recipe first | Users repeatedly need per-task restore and someone owns persistence/security review |
| Source builds vs prebuilt release | Stabilize source-built preview first | Install time and toolchain failures demonstrably block adoption |
| Persistent memory vs project docs | Small reviewed project notes | Retrieval quality—not merely storage—is shown to be the bottleneck |
| More agents vs better lead workflow | Improve the lead and result review first | Work is independent, integration is cheap, and measured total cost is acceptable |

## 8. First ten implementation-sized tickets

These are a suggested backlog, not tasks authorized or executed by this research.

Effort: **S** ≈ 0.5–2 days, **M** ≈ 3–5 days, **L** ≈ 1–2+ weeks; estimates include focused verification but not external clearance.

| Order | Ticket / owner | Size | Dependency / definition of done |
| --- | --- | --- | --- |
| 1 | **R00 Baseline/provenance agreement** · root/core | M | Identify canonical candidate; recipe, source, docs and installed capabilities reconcile without losing current features |
| 2 | **UX01 Queue visibility under height pressure** · core | S–M | R00; reproduce first; minimal persistent indication plus focused PTY evidence |
| 3 | **UX03 Configured keyboard/help map** · core/docs | S | R00; real bindings, focus return and no new collisions |
| 4 | **UX02 Attention-state precedence** · core/plugins | M | R00; concurrent waiting/retry/stopping/failure cases remain truthful |
| 5 | **UX07 Check evidence contract** · Lens/core | M | Agree ownership; exact scope/source, stale invalidation and visible failure |
| 6 | **UX12 Review entry point / Plannotator pilot** · integration | S–M | R00; preserve route, draft, existing edits and plan intent |
| 7 | **UX05/06/14 Input/accessibility acceptance pass** · core | M | Current candidate; terminal/theme/IME evidence, fixes only where reproduced |
| 8 | **R03a Recovery playbook and drill** · manager/docs | M | Distinct code/profile/workspace recovery, safe restore preview and interrupted-path evidence |
| 9 | **R03b Isolated autonomous reference workflow** · integration/security | L | Approved boundary and unchanged billing route; nested-call and credential exposure tests |
| 10 | **R06 Public preview readiness packet** · release | L+ | Clearance, anonymous pins, platform/install/recovery gates and accurate publication status |

If only one week is available: baseline alignment, queue/attention reproduction, keyboard help and a Plannotator trial. **Do not spend it adding long-term memory or another agent manager.**

## 9. Measure whether the changes help

Avoid invented benchmarks. Establish a baseline on the actual candidate and representative projects first.

| Measure | Why it matters | Proposed success criterion |
| --- | --- | --- |
| Draft integrity across focus/resize/stop | Input is the primary control | Zero lost/duplicated draft content in the agreed acceptance scenarios |
| Time to find an agent failure or pending approval | Hidden states cause stalls | Reach the responsible item in one documented action from the summary |
| Verification truth | Confidence must track evidence | Every displayed pass has scope/source; relevant edits make it stale |
| Startup readiness | Plugin growth can slow every session | Record cold/warm managed-launch p50/p95, not just direct CLI help; no unexplained regression |
| Input/render responsiveness | Slow tooling should not block typing | Capture an actual baseline; set budget after measurement, including short terminals |
| Context overhead | More tools/instructions can reduce useful context | Compare prompt/tool-description size and task success with each optional addition |
| Agent usefulness | Parallelism can waste work | Accepted independent results and total review time, not spawned-agent count |
| Recovery success | A backup is only useful if restorable | Disposable restore drill preserves unrelated and untracked work or explicitly refuses |
| New-user first task | Installation is part of UX | Supported-platform clean install → explicit login → one read-only task, with no undocumented manual repair |
| Integration maintenance | Optional tools should stay optional | Each has owner, version, health, disable/remove and data-retention instructions |

Collect local evidence by default. Product telemetry would be a separate privacy decision, not a silent prerequisite.

## 10. Verification record and limits

### What this research checked

- Repository HEAD, submodule status, existing dirty-file inventory, recipe, relevant architecture/user/publication/verification docs, and source paths for native UI behavior.
- Installed release metadata: Pi 1.0.0 and different source revision; relevant installed MCP, sessions, configuration, packages, skills, security and isolation documentation.
- Anonymous GitHub REST metadata for the root, tags, releases and four fork URLs.
- npm registry `latest` metadata for Plannotator, Context7 Pi, permission-system, pi-memory and Playwright CLI. Listed versions are a **dated observation**, not a promise that they remain latest.
- Official maintainer documentation for proposed integrations and competing-agent patterns; skills.sh and GitHub adoption signals for the optional React skill.
- Artifact checks: a Python local-link/XML/whitespace validator passed (25 local links); `git diff --check` passed. Chrome rendered the 1760×4450 SVG; inspection of its 165 text elements found no canvas/card text overflow, and a full-page screenshot was visually reviewed.
- `lens_diagnostics(mode="all")`: no blocking errors; one Marksman warning incorrectly reports the Lens README link missing. Direct filesystem and local-link validation confirm `plugins/attro-lens/README.md` exists. This is an artifact diagnostic, not a product-wide check.

### Not established

- Runtime correctness, visual accessibility, latency or cancellation behavior of the current dirty Attro source.
- Compatibility or security of third-party packages with this custom fork, despite semver matches.
- Full local personal-plugin inventory, credentials, authenticated MCP health, provider availability or pricing.
- Current public CI status beyond the dated project records; the old “failed CI” statement is historical, not a fresh CI claim.
- A clean release build, anonymous recursive install, platform certification, or approved publication clearance.
- Security of all historical Git objects. The documented retained-object issue is a release gate, not a new claim that live secrets were found.

Do not rerun full product suites merely because a research document was added. Implementations should run their owning project's required gates and focused regression checks, with current revision/diff recorded. No product tests were run for this report.

## 11. Sources and evidence index

External sources accessed 12–13 October 2026. Maintainer READMEs describe intended behavior, not independent certification. Where current web docs differ from the pinned host, the host/version matrix wins.

### Local evidence

- **L1:** [Recipe](../../attro.json), [source lock](../../sources.lock.json), [root README](../../README.md), [contributor checks](../../CONTRIBUTING.md).
- **L2:** [Native transcript ownership and controls](../design/transcript-ui.md), [dock design/evidence](../archive/dock-plan.md), [native parity](../archive/zentui-native-parity.md).
- **L3:** [Using Attro](../using-attro.md), [retired effort plan](../archive/effort-profiles-plan.md), [historical effort implementation](../archive/effort-profiles-implementation.md).
- **L4:** [Publication gates](../maintainers/publication.md), [release procedure](../maintainers/releasing.md), [recorded verification](../maintainers/verification.md), [update automation](../maintainers/automation.md).
- **L5:** [Security](../../SECURITY.md), [managed profile/recovery](../../profile/MANAGED.md), [initial settings](../../profile/settings.json).
- **L6:** [Subagents](../../plugins/attro-subagents/README.md), [Lens](../../plugins/attro-lens/README.md), [RPIV](../../plugins/attro-rpiv/README.md).
- **L7:** Installed artifact `~/.attro/releases/attro-0.2.0-c93e3582ecdc/manifest.json`; `pi/packages/coding-agent/package.json`; docs `mcp.md`, `sessions.md`, `security.md`, `containerization.md`, `packages.md`, `skills.md`, `configuration.md`. Local-only evidence; not assumed to be the current root gitlink.
- **L8:** Anonymous availability endpoints: [root](https://api.github.com/repos/ernestjsf/attro), [tags](https://api.github.com/repos/ernestjsf/attro/tags), [releases](https://api.github.com/repos/ernestjsf/attro/releases). Fork endpoints used the same `/repos/ernestjsf/attro-{core,lens,rpiv,subagents}` pattern.

### External evidence

- **E1:** [Plannotator Pi integration](https://github.com/backnotprop/plannotator/blob/main/apps/pi-extension/README.md); [privacy/network behavior](https://github.com/backnotprop/plannotator#privacy-and-network-behavior); [registry metadata](https://registry.npmjs.org/@plannotator/pi-extension/latest).
- **E2:** [Context7 maintained documentation](https://github.com/upstash/context7); [native Pi registry metadata](https://registry.npmjs.org/@upstash/context7-pi/latest).
- **E3:** [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp), especially usage statistics, CrUX and browser-content exposure.
- **E4:** [Microsoft Playwright CLI](https://github.com/microsoft/playwright-cli), [Playwright MCP](https://github.com/microsoft/playwright-mcp), [CLI registry metadata](https://registry.npmjs.org/@playwright/cli/latest).
- **E5:** [Vercel agent skills](https://github.com/vercel-labs/agent-skills), [React skill source](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md), [skills.sh entry](https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices), [GitHub metadata](https://api.github.com/repos/vercel-labs/agent-skills).
- **E6:** [Pi isolation reference](https://pi.dev/docs/latest/containerization), [Pi security](https://pi.dev/docs/latest/security), [Gondolin](https://github.com/earendil-works/gondolin). Installed docs were the primary baseline for the tool-only/whole-process distinction.
- **E7:** [Permission-system README and non-goals](https://github.com/gotgenes/pi-packages/tree/main/packages/pi-permission-system), [registry peer requirements](https://registry.npmjs.org/@gotgenes/pi-permission-system/latest).
- **E8:** [pi-memory source/README](https://github.com/jayzeng/pi-memory), [registry requirements](https://registry.npmjs.org/pi-memory/latest).
- **E9:** [Claude Code checkpoints](https://code.claude.com/docs/en/checkpointing), [permissions](https://code.claude.com/docs/en/permissions).
- **E10:** [Codex security](https://developers.openai.com/codex/security/) (redirected to ChatGPT Learn during retrieval).
- **E11:** [OpenCode permissions](https://opencode.ai/docs/permissions/), [agents](https://opencode.ai/docs/agents/), [MCP](https://opencode.ai/docs/mcp-servers/).
- **E12:** [Aider lint/test workflow](https://aider.chat/docs/usage/lint-test.html).
- **E13:** [Gemini CLI checkpointing](https://geminicli.com/docs/cli/checkpointing/), [session management](https://geminicli.com/docs/cli/session-management/).
- **E14:** [Pi packages](https://pi.dev/docs/latest/packages), [package catalog](https://pi.dev/packages), [skills](https://pi.dev/docs/latest/skills), [extensions](https://pi.dev/docs/latest/extensions).
- **E15:** [W3C keyboard-interface guidance](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/), [animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html). Web semantics/ARIA do not directly apply to an ANSI terminal renderer.

**Bottom line:** align the baseline, polish the controls, attach evidence to outcomes, make recovery explicit, then add only the integrations that prove their value. That is a stronger Attro than a larger plugin bundle.
