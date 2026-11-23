# Pi + zmx

zmx is installed from the Homebrew formula `neurosnap/tap/zmx`, declared in
`zmx/Brewfile`. Run `mise zmx:install` explicitly; preview configuration with
`mise zmx:plan`, then deploy with `mise zmx:apply`. `mise fish:apply` deploys the
optional `zpi` wrapper; ordinary `pi` does not need zmx. `zmx.fish` sets one private socket directory for local and SSH Fish
shells: `~/.local/state/zmx`.

## Use

Open a new Fish shell and run `zpi` to start Pi in a new zmx session
named `<directory>-<two random a-z0-9>`.
Existing names are skipped. Arguments are passed unchanged.

```fish
zpi
zmx list
zmx attach dotfiles-k7
```

- Close the terminal or press `Ctrl+\` to detach; Pi keeps running.
- Exit Pi (`/quit`, or `Ctrl+D` with an empty editor) to end its zmx session.
- `zmx detach` detaches all clients, not just the current one.
- Run `pi` without a wrapper when you do not need a zmx session.
- Scripts, pipes, redirected streams, print/JSON/RPC modes, help/version, and
  management commands bypass zmx. `--mode text` remains interactive.
- Inside an existing zmx session, Pi runs directly without nesting. That existing
  session is not owned or cleaned up by this wrapper.

Connect to the same machine and user over SSH:

```sh
ssh your-mac '/opt/homebrew/bin/zmx list'
ssh -t your-mac '/opt/homebrew/bin/zmx attach dotfiles-k7'
```

These examples assume Fish is the remote login shell, so its non-interactive
startup loads `ZMX_DIR`. Otherwise set `ZMX_DIR` in that shell too.
`attach` creates a shell when the named session no longer exists; select a live
name from `zmx list`. Rebooting the machine ends the processes.

The two-character suffix has 1,296 combinations per directory label. It is a
short human-friendly identifier, not a concurrency lock: simultaneous launches
can theoretically choose the same unused name. No lock or session database is
maintained. Pi conversation names remain independent and can change via `/name`.

Use zmx's native list/attach.

## Check

```sh
fish --no-config -n fish/functions/zpi.fish zmx/zmx.fish
python3 zmx/test_pi.py
```

The wrapper tests use fake Pi/zmx commands in a pseudo-terminal.
