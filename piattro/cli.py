"""Piattro commands for explicitly trusted local checkouts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from piattro import __version__
from piattro.doctor import run_doctor
from piattro.launch import build_exec_env, build_try_env, exec_pi, normalize_pi_command, populate_try_agent, refuse_managed_mutation, resolve_pi_binary
from piattro.lock import operation_lock
from piattro.paths import home, release_dir, validate_state_root
from piattro.prepare import prepare_release
from piattro.state import activate_release, active_release_path, load_state, prepared_manifest, register_release, rollback
from piattro.validate import ValidationError, validate_release_id


def emit(args: argparse.Namespace, data: object, message: str) -> None:
    print(json.dumps(data, indent=2, sort_keys=True) if args.json else message)


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
    emit(args, manifest, f"prepared release {rid}" + (" (active)" if args.activate else ""))
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
    message = "Piattro doctor: " + ("OK" if report["healthy"] else "issues found")
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
    emit(args, {"active": args.release_id}, f"activated {args.release_id}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    with operation_lock(args.root):
        previous = rollback(args.root)
    emit(args, {"active": previous}, f"rolled back to {previous}; live ~/.pi data is untouched")
    return 0


def _launch(args: argparse.Namespace, trial: bool) -> int:
    if args.json and not args.dry_run:
        raise ValidationError("--json is supported for launch commands only with --dry-run")
    if trial and args.release_id:
        validate_release_id(args.release_id)
        if args.release_id not in load_state(args.root)["releases"]:
            raise ValidationError(f"unknown release: {args.release_id}")
        release = release_dir(args.release_id, args.root)
        prepared_manifest(release, args.release_id)
    else:
        release = active_release_path(args.root)
    if release is None:
        raise ValidationError("no active release; run setup --repo PATH --activate first")
    command = normalize_pi_command(list(args.command))
    refuse_managed_mutation(command)
    pi_bin = resolve_pi_binary(release)

    def run(env: dict[str, str]) -> int:
        if args.dry_run:
            data = {"argv": [pi_bin, *command], "agentDir": env["PI_CODING_AGENT_DIR"], "releaseRoot": env["PIATTRO_RELEASE_ROOT"]}
            emit(args, data, f"would run: {' '.join(data['argv'])}\nPI_CODING_AGENT_DIR={data['agentDir']}\nPIATTRO_RELEASE_ROOT={data['releaseRoot']}")
            return 0
        if trial:
            return subprocess.run([pi_bin, *command], env=env, check=False).returncode
        exec_pi(pi_bin, command, env)
        return 0

    if not trial:
        return run(build_exec_env(release))
    with tempfile.TemporaryDirectory(prefix="piattro-try-") as tmp:
        agent = Path(tmp) / "agent"
        populate_try_agent(release, agent)
        return run(build_try_env(release, agent))


def cmd_try(args: argparse.Namespace) -> int:
    return _launch(args, True)


def cmd_exec(args: argparse.Namespace) -> int:
    return _launch(args, False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="piattro", description="Isolated release manager; trusted local checkouts only, not an OS sandbox.")
    parser.add_argument("--version", action="version", version=f"piattro {__version__}")
    parser.add_argument("--json", action="store_true", help="emit JSON (launch commands require --dry-run)")
    parser.add_argument("--state-root", help="managed directory (default: ~/.piattro or PIATTRO_HOME)")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    for name in ("setup", "update"):
        command = sub.add_parser(name, help="prepare a release from a trusted, clean local checkout")
        command.add_argument("--repo", required=True, help="explicit trusted pi-customizations checkout")
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
    args = build_parser().parse_args(argv)
    try:
        args.root = validate_state_root(Path(args.state_root).expanduser() if args.state_root else home())
        return args.func(args)
    except (ValidationError, OSError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        if args.json:
            print(json.dumps({"error": "interrupted"}))
        else:
            print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
