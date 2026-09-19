"""Attro commands for explicitly trusted local checkouts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

from attro import __version__
from attro.doctor import run_doctor
from attro.launch import build_exec_env, build_try_env, exec_pi, managed_resource_args, normalize_pi_command, populate_try_agent, refuse_managed_mutation, resolve_pi_binary
from attro.lock import LAUNCH_LOCK_WAIT_SECONDS, operation_lock
from attro.retention import filter_launch_retention_warnings, reconcile_and_maybe_reap, release_lease
from attro.paths import home, release_dir, validate_state_root
from attro.prepare import prepare_release
from attro.state import activate_release, load_state, prepared_manifest, register_release, rollback
from attro.validate import ValidationError, validate_release_id

MANAGEMENT_SUBCOMMANDS = frozenset(
    {
        "setup",
        "update",
        "status",
        "doctor",
        "activate",
        "rollback",
        "try",
        "exec",
    }
)


def emit(args: argparse.Namespace, data: object, message: str) -> None:
    print(json.dumps(data, indent=2, sort_keys=True) if args.json else message)


def split_argv(argv: list[str]) -> tuple[dict[str, object], list[str]]:
    json_flag = False
    state_root: str | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--json":
            json_flag = True
            index += 1
            continue
        if token.startswith("--state-root="):
            state_root = token.partition("=")[2]
            index += 1
            continue
        if token == "--state-root":
            if index + 1 >= len(argv):
                raise ValidationError("--state-root requires a value")
            state_root = argv[index + 1]
            index += 2
            continue
        if token == "--version":
            print(f"attro {__version__}")
            raise SystemExit(0)
        break
    return {"json": json_flag, "state_root": state_root}, argv[index:]


def is_management_argv(argv: list[str]) -> bool:
    _, body = split_argv(argv)
    return bool(body) and body[0] in {*MANAGEMENT_SUBCOMMANDS, "--help", "-h"}


def everyday_command(argv: list[str]) -> list[str]:
    _, body = split_argv(argv)
    if body and body[0] == "--":
        return body[1:]
    return body


def _emit_retention_result(args: argparse.Namespace, data: object, message: str, warnings: list[str]) -> None:
    if warnings and args.json and isinstance(data, dict):
        data = {**data, "warnings": warnings}
    emit(args, data, message)
    if warnings and not args.json:
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)


def cmd_setup(args: argparse.Namespace) -> int:
    checkout = Path(args.repo).expanduser().resolve()
    state_root = validate_state_root(args.root, checkout)
    with operation_lock(state_root):
        load_state(state_root)
        manifest = prepare_release(checkout, state_root=state_root)
        rid = manifest["releaseId"]
        register_release(state_root, rid, release_dir(rid, state_root))
        if args.activate:
            activate_release(state_root, rid)
        warnings = reconcile_and_maybe_reap(state_root)
    _emit_retention_result(args, manifest, f"prepared release {rid}" + (" (active)" if args.activate else ""), warnings)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(args.root)
    message = f"state root: {args.root}\nactive: {state['active'] or '(none)'}\nprevious: {state['previous'] or '(none)'}\nreleases: {len(state['releases'])}"
    for rid in sorted(state["releases"]):
        message += f"\n  {rid}"
    emit(args, state, message)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve() if args.repo else None
    report = run_doctor(repo=repo, state_root=args.root)
    message = "Attro doctor: " + ("OK" if report["healthy"] else "issues found")
    for issue in report["issues"]:
        message += f"\n  issue: {issue}"
    for warning in report["warnings"]:
        message += f"\n  warning: {warning}"
    emit(args, report, message)
    return 0 if report["healthy"] else 1


def cmd_activate(args: argparse.Namespace) -> int:
    validate_release_id(args.release_id)
    with operation_lock(args.root):
        activate_release(args.root, args.release_id)
        warnings = reconcile_and_maybe_reap(args.root)
    _emit_retention_result(args, {"active": args.release_id}, f"activated {args.release_id}", warnings)
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    with operation_lock(args.root):
        previous = rollback(args.root)
        warnings = reconcile_and_maybe_reap(args.root)
    _emit_retention_result(args, {"active": previous}, f"rolled back to {previous}; live ~/.pi data is untouched", warnings)
    return 0


def _launch(args: argparse.Namespace, trial: bool) -> int:
    if args.json and not args.dry_run:
        raise ValidationError("--json is supported for launch commands only with --dry-run")
    command = normalize_pi_command(list(args.command))
    refuse_managed_mutation(command)

    def resolve(state: dict) -> tuple[str, Path]:
        if trial and args.release_id:
            validate_release_id(args.release_id)
            if args.release_id not in state["releases"]:
                raise ValidationError(f"unknown release: {args.release_id}")
            release_id = args.release_id
        else:
            if state["active"] is None:
                raise ValidationError("no active release; run setup --repo PATH --activate first")
            release_id = state["active"]
        if state["releases"].get(release_id, {}).get("deleting"):
            raise ValidationError(f"release is marked deleting: {release_id}")
        return release_id, release_dir(release_id, args.root)

    def run(pi_bin: str, full_command: list[str], env: dict[str, str], lease_fd: int | None = None) -> int:
        if args.dry_run:
            data = {"argv": [pi_bin, *full_command], "agentDir": env["PI_CODING_AGENT_DIR"], "releaseRoot": env["ATTRO_RELEASE_ROOT"], "resourceDir": env["ATTRO_RESOURCE_DIR"]}
            emit(args, data, f"would run: {' '.join(data['argv'])}\nPI_CODING_AGENT_DIR={data['agentDir']}\nATTRO_RELEASE_ROOT={data['releaseRoot']}\nATTRO_RESOURCE_DIR={data['resourceDir']}")
            return 0
        if trial:
            return subprocess.run([pi_bin, *full_command], env=env, check=False, pass_fds=() if lease_fd is None else (lease_fd,)).returncode
        exec_pi(pi_bin, full_command, env)
        return 0

    if args.dry_run:
        state = load_state(args.root)
        _, release = resolve(state)
        manifest = prepared_manifest(release, release.name)
        pi_bin = resolve_pi_binary(release, manifest=manifest)
        full_command = [*managed_resource_args(release, manifest=manifest), *command]
        env = build_try_env(release, Path(tempfile.gettempdir()) / "attro-try-<temporary>" / "agent", manifest=manifest) if trial else build_exec_env(release, manifest=manifest)
        return run(pi_bin, full_command, env)

    with ExitStack() as leases:
        with operation_lock(args.root, wait_timeout=LAUNCH_LOCK_WAIT_SECONDS):
            state = load_state(args.root)
            release_id, release = resolve(state)
            lease = leases.enter_context(release_lease(release, inheritable=True))
            manifest = prepared_manifest(release, release_id)
            pi_bin = resolve_pi_binary(release, manifest=manifest)
            full_command = [*managed_resource_args(release, manifest=manifest), *command]
            warnings = filter_launch_retention_warnings(reconcile_and_maybe_reap(args.root))
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if not trial:
            return run(pi_bin, full_command, build_exec_env(release, manifest=manifest), lease.fd)
        with tempfile.TemporaryDirectory(prefix="attro-try-") as tmp:
            agent = Path(tmp) / "agent"
            populate_try_agent(release, agent, manifest=manifest)
            return run(pi_bin, full_command, build_try_env(release, agent, manifest=manifest), lease.fd)


def cmd_try(args: argparse.Namespace) -> int:
    return _launch(args, True)


def cmd_exec(args: argparse.Namespace) -> int:
    return _launch(args, False)


def _everyday_launch(opts: dict[str, object], command: list[str], root: Path) -> int:
    args = argparse.Namespace(
        json=opts["json"],
        dry_run=False,
        command=command,
        release_id=None,
        root=root,
        state_root=opts["state_root"],
    )
    return _launch(args, False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="attro",
        description="Run attro without a subcommand to open the coding app. Management commands use trusted local checkouts; this is not an OS sandbox.",
        epilog="Use attro -- --help for Pi options, or attro -- doctor to forward doctor to the app. Pi package-management mutations remain blocked.",
    )
    parser.add_argument("--version", action="version", version=f"attro {__version__}")
    parser.add_argument("--json", action="store_true", help="emit JSON (launch commands require --dry-run)")
    parser.add_argument("--state-root", help="managed directory (default: ~/.attro, legacy ~/.piattro, ATTRO_HOME, or PIATTRO_HOME)")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    for name in ("setup", "update"):
        command = sub.add_parser(name, help="prepare a release from a trusted, clean local checkout")
        command.add_argument("--repo", required=True, help="explicit trusted attro checkout")
        command.add_argument("--activate", action="store_true")
        command.set_defaults(func=cmd_setup)
    sub.add_parser("status", help="show activation state").set_defaults(func=cmd_status)
    doctor = sub.add_parser("doctor", help="check retained releases and optionally a source checkout")
    doctor.add_argument("--repo")
    doctor.set_defaults(func=cmd_doctor)
    activate = sub.add_parser("activate", help="activate a retained release")
    activate.add_argument("release_id")
    activate.set_defaults(func=cmd_activate)
    sub.add_parser("rollback", help="switch back to the previous retained release").set_defaults(func=cmd_rollback)
    for name, func in (("try", cmd_try), ("exec", cmd_exec)):
        command = sub.add_parser(name, help="run retained Pi; use -- before Pi flags")
        if name == "try":
            command.add_argument("--release-id")
        command.add_argument("--dry-run", action="store_true")
        command.add_argument("command", nargs=argparse.REMAINDER)
        command.set_defaults(func=func)
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_mode = False
    try:
        opts, _ = split_argv(raw)
        json_mode = bool(opts["json"])
        state_root_value = opts["state_root"]
        root = validate_state_root(Path(state_root_value).expanduser() if isinstance(state_root_value, str) else home())
        if is_management_argv(raw):
            args = build_parser().parse_args(raw)
            args.root = root
            return args.func(args)
        return _everyday_launch(opts, everyday_command(raw), root)
    except SystemExit as exc:
        raise exc
    except (ValidationError, OSError) as exc:
        if json_mode:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        if json_mode:
            print(json.dumps({"error": "interrupted"}))
        else:
            print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
