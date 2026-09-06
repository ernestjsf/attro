"""Guardrails for managed Pi launches."""

from __future__ import annotations

MANAGED_REFUSAL = (
    "attro-managed releases pin packages and core via attro setup/update; "
    "native pi package/core mutations are refused. "
    "Use `bin/attro update` to stage a new release and `bin/attro activate` to switch. "
    "See profile/MANAGED.md."
)

# Pi subcommands that mutate installed packages or the core CLI outside Attro.
BLOCKED_PI_COMMANDS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("update",),
        ("install",),
        ("remove",),
        ("uninstall",),
        ("upgrade",),
    }
)


def blocked_pi_command(argv: list[str]) -> tuple[str, ...] | None:
    """Return the blocked command prefix if argv starts a refused pi mutation."""
    if not argv:
        return None
    first = argv[0]
    if first in {"update", "install", "remove", "uninstall", "upgrade"}:
        return (first,)
    if first == "package" and len(argv) >= 2:
        sub = argv[1]
        if sub in {"install", "remove", "uninstall", "update", "upgrade"}:
            return ("package", sub)
    return None
