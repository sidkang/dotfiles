#!/usr/bin/env python3
"""Exercise the Fish wrapper with fake commands and a real pseudo-terminal."""
import json
import os
from pathlib import Path
import pty
import select
import shlex
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FISH = "/opt/homebrew/bin/fish"


def terminal(command, env, cwd):
    master, slave = pty.openpty()
    proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, env=env, cwd=cwd)
    os.close(slave)
    output = bytearray()
    deadline = time.monotonic() + 10
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
            if proc.poll() is not None:
                break
        proc.wait(timeout=2)
        return proc.returncode, output.decode(errors="replace")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)


def main():
    with tempfile.TemporaryDirectory(prefix="pi-wrapper-") as temp:
        base = Path(temp)
        project = base / "project space"
        project.mkdir()
        log = base / "calls.jsonl"
        for name in ("pi", "zmx"):
            script = base / name
            script.write_text("#!/usr/bin/env python3\n" + '''import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
if name == "zmx" and sys.argv[1:3] == ["list", "--short"]:
    print("project-space-aa")
else:
    with open(os.environ["CALL_LOG"], "a") as f:
        f.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
sys.exit(17 if name == "pi" else 0)
''')
            script.chmod(0o755)
        env = {**os.environ, "PATH": f"{base}:/opt/homebrew/bin:/usr/bin:/bin", "CALL_LOG": str(log), "TERM": "xterm-256color"}
        env.pop("ZMX_SESSION", None)
        source = f"source {shlex.quote(str(ROOT / 'fish/functions/pi.fish'))}; "
        cases = [
            ([], True), (["-c"], True), (["-r"], True),
            (["--mode", "text"], True), (["--", "--print"], True),
            (["--name", "--print", "a prompt with spaces"], True),
            (["-p", "hello"], False), (["--mode", "rpc"], False),
            (["--mode", "json"], False), (["--help"], False),
            (["--version"], False), (["--export", "x"], False),
            (["--list-models"], False), (["update", "--extensions"], False),
            (["auth", "check"], False), (["mcp", "list"], False),
        ]
        for args, wrapped in cases:
            code, output = terminal([FISH, "--no-config", "-ic", source + "pi " + shlex.join(args)], env, project)
            call = json.loads(log.read_text().splitlines()[-1])
            assert call[0] == ("zmx" if wrapped else "pi"), (args, call, output)
            assert code == (0 if wrapped else 17), (args, code, output)
            if wrapped:
                assert call[1] == "attach" and call[2].startswith("project-space-")
                assert len(call[2].removeprefix("project-space-")) == 2
                assert call[3:] == [str(base / "pi"), *args], call
            else:
                assert call[1:] == args, call
        # Non-interactive shell, redirected stdin/stdout, and nested zmx bypass.
        for options, body, extra in [
            (["-c"], "pi", {}),
            (["-ic"], "pi </dev/null", {}),
            (["-ic"], "pi >/dev/null", {}),
            (["-ic"], "pi", {"ZMX_SESSION": "existing"}),
        ]:
            code, output = terminal([FISH, "--no-config", *options, source + body], {**env, **extra}, project)
            assert json.loads(log.read_text().splitlines()[-1]) == ["pi"], output
            assert code == 17, (code, output)
        # Force aa (occupied), then bb, without making production code injectable.
        random = "function random; set -g draws (math 1 + $draws); if test $draws -le 2; echo a; else; echo b; end; end; set -g draws 0; "
        code, output = terminal([FISH, "--no-config", "-ic", source + random + "pi"], env, project)
        call = json.loads(log.read_text().splitlines()[-1])
        assert code == 0 and call[2] == "project-space-bb", (call, output)
        print(f"PASS: {len(cases) + 5} wrapper cases (routing, arguments, exit status, collision retry)")


if __name__ == "__main__":
    main()
