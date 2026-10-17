# Using Attro

Attro is a source-built developer preview. Check the [current availability](../README.md#install)
before installing; a public root repository alone does not make its private
source dependencies installable. The software is MIT-licensed; model access is
separate and may require a paid subscription or metered API credits.

## First session

After a successful installation:

```sh
export PATH="$HOME/.local/bin:$PATH"
attro --version
attro doctor
cd /path/to/your/project
attro
```

Use your chosen `--bin-dir` instead if you changed it. The installer prints the
PATH line but does not change shell startup files. Keep the source checkout in
place: the launcher is a symlink to its `bin/attro`.

Run `/login` to connect a provider, then `/model` to choose an available model.
Use only an account you are authorized to use. API-key and subscription routes
can have different billing and limits; a subscription does not necessarily
include API credits. Attro does not provide an account, free model credits, or a
guarantee that a particular model is available to your account.

Choose the lead model with `/model` and its reasoning level with `/thinking`.
In either picker, press Ctrl+S to save the selection as a startup default.
Named subagents use their agent-definition defaults; explicit task overrides
remain available. See [model selection](../plugins/attro-core/packages/coding-agent/docs/models.md)
and [subagent configuration](../plugins/pi-subagents/README.md#agent-definitions).

Effort profiles, their selector, and profile suggestions have been removed from
source. Old session history remains readable, including its recorded lead
model/thinking, but profile team mappings no longer control routing. Navigating
to a root or branch without recorded model/thinking keeps the current choices;
retired profile baselines are not restored. Existing installations retain the feature until a release
containing this change is prepared and activated. Before switching, transfer
any desired lead settings to `settings.json` and specialist settings to their
agent definitions; personal catalogs are not automatically migrated or deleted.

Start with a task that does not request changes:

```text
Explain this project's structure and how to run its checks. Do not edit files.
```

Then request a small change and review its diff. Tools and extensions run with
your user permissions; neither project trust nor `attro try` is a sandbox. See
[security and privacy](../SECURITY.md) before using untrusted code or unattended
agents. Additional agents and provider features can consume additional tokens.
The pinned core enables streaming cache warming by default, which can make
additional provider requests; inspect provider settings and billing limits.

## Resume and configuration

```sh
attro --continue
```

Or use `/resume` inside Attro. Sessions, login, settings, and personal resources
live in `~/.attro/agent`. `ATTRO_HOME` changes the parent directory; export the
same value for install and every launch. Legacy `~/.piattro` may be reused when
`~/.attro` is absent. `attro status` reports the actual managed root.

No credentials or sessions are imported from `~/.pi/agent`. Do not share token
files between the two installations. Back up your profile securely; it may
contain credentials, private prompts, file contents, and command output. Never
attach a whole profile or session to a public issue without reviewing and
redacting it.

## Update deliberately

There is no automatic stable update feed. `attro update` prepares an explicit,
reviewed source recipe; it does not fetch a new release for you.

Once a new reviewed release tag is available, obtain a clean recursive checkout
of it. In the following command replace `<published-tag>` with that actual tag:

```sh
git clone --recurse-submodules --branch <published-tag> \
  https://github.com/ernestjsf/attro.git /path/to/new-checkout
attro update --repo /path/to/new-checkout
attro activate <release-id-printed-by-update>
attro doctor
```

Keep the original launcher checkout at its existing path. Preparing from another
checkout does not update the Python manager behind that launcher. If release
notes require a manager update, update the original checkout to the reviewed
tag with Git only after preserving local work, update its submodules, and rerun
`./install` there. Do not delete or replace an existing checkout blindly.

Activation preserves the shared profile. Running sessions retain their release;
start a new session to use new code. Superseded idle releases are automatically
pruned. `attro rollback` works only while the previous release is retained; it
is not a backup and does not undo user data or external changes. If old code is
already gone, prepare its reviewed source recipe again. See
[update and retention details](../README.md#update-and-rollback).

## Uninstall without losing your work

There is no managed `attro uninstall` command. Do not use upstream package
removal commands to modify a prepared release.

1. Exit Attro and its child agents, and allow release cleanup to finish. Do not
   remove code while sessions or background cleanup still use it.
2. Run `command -v attro` and inspect that path with `ls -l`. Remove **only the
   launcher symlink you installed**, after confirming it points to the expected
   checkout. The default link is `~/.local/bin/attro`; a custom bin directory
   may differ. Leave unrelated `pi` launchers alone.
3. Keep the source checkout and managed state until you are sure no processes
   use them and you have backed up any work. Removing the launcher alone
   disables that installation without deleting credentials or sessions.
4. Optional complete removal: after checking `attro status` before removing the
   launcher and securely backing up the profile, remove only the confirmed
   Attro source directory and managed root. This permanently deletes local
   credentials and history if you include the profile. Review paths manually;
   do not delete `~/.pi` or other projects.

Deleting local credentials does not necessarily revoke provider sessions or API
keys. Revoke them through the provider when appropriate. Remove a shell PATH
entry only if you added it solely for Attro; `~/.local/bin` commonly contains
other applications.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `attro: command not found` | Add the installer's bin directory to PATH and open a new shell. |
| Clone reports repository not found | All four pinned forks must be public or explicitly accessible to you. A root-only clone is insufficient. |
| Bootstrap refuses an existing directory | Inspect it; do not delete it blindly. Resume a trusted, complete checkout with `./install`, or use a new `ATTRO_SOURCE_DIR`. |
| Python or Node version error | Check `python3 --version`, `node --version`, and PATH; Python 3.10+ and Node 22.19.0+ are required. |
| No active release | Finish `./install` from the trusted checkout, or prepare and activate a release explicitly. |
| Missing model | Authenticate with `/login`, select an available `/model`, and save the startup default if desired. |
| Update did not change the running session | Activate the prepared release and start a new session. Check `attro status`. |
| Rollback target is unavailable | Idle code may have been pruned; prepare the desired reviewed recipe again. |

For bugs, include OS/architecture, Python/Node versions, `attro --version`, the
source revision, and a minimal reproduction. Review `attro doctor` output before
sharing it: paths may identify you. Use the [issue tracker](https://github.com/ernestjsf/attro/issues)
for non-sensitive reports and [SECURITY.md](../SECURITY.md) for vulnerabilities.
