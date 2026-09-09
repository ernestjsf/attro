# Native bottom dock implementation plan

## Approved direction

Attro core owns one bottom dock. Preserve the native editor and its editing,
completion, paste, history, and focus behavior. Place compact task and agent
sections below the composer; expanded lists share a height budget and full
content remains available through existing detail interfaces. Background updates
must not reopen sections or steal the draft's focus.

Plugins continue to own task, agent, and diagnostic functionality. Integrate
presentation at a small shared seam rather than duplicating their state or
introducing a dashboard framework. Ordinary extension widgets retain a fallback.
Use the active theme and configurable keybindings; do not copy browser shortcuts.

## Checkpoints

1. Map core layout/editor ownership and plugin contribution points. Agree on the
   concrete contribution contract before parallel implementation.
2. Implement the native dock and bounded section rendering. Preserve the editor
   instance, exceptional activity/cancellation, and regular-mode operation.
   Run core-required checks and commit the verified core increment locally.
3. Adapt task and agent presentation to the shared dock without changing tools,
   execution, delivery, or persistence. Preserve existing detail actions and
   expose attention even when collapsed. Check and commit the plugin increments.
4. Review the integrated task diff independently. Verify real terminal rendering
   at wide/narrow and short sizes, draft/focus retention, and detail navigation.
   Correct concrete findings, document evidence and limits, then commit release
   source pins and documentation.

## Interaction priorities

- Input remains primary. Growing drafts take space before expanded lists.
- Empty sections take no rows; completed work remains inspectable.
- Waiting and failed agents remain discoverable, including alongside queued input.
- Steering and follow-up retain their actual semantics and configured shortcuts.
- Keyboard paths work without a mouse or overriding editor completion keys.
- Fullscreen mouse handling must not break transcript selection or scrolling.
- Resizing can shorten a list without changing the user's expansion preference.
- Details return to the untouched draft; plugin reload removes stale UI state.

## Scope and verification boundary

No new dependencies, live profile changes, installed-release modifications,
activation, publication, or push. Local commits are authorized. Release input
pins must refer to actual committed source; do not conceal failing checks by
weakening verification. Use isolated terminals and synthetic/local data instead
of paid provider calls. Record any interaction not exercised rather than treating
the HTML prototype as native-rendering evidence.

The reference prototype is currently `/private/tmp/attro-dock-preview/index.html`.
It is design evidence only, not production code or a durable release artifact.
