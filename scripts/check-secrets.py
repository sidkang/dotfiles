#!/usr/bin/env python3
"""Scan only versioned working files, then repository history."""
from pathlib import Path
import shutil
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[1]


def main():
    brew = shutil.which("brew")
    if brew is None:
        raise SystemExit("Missing Homebrew; checks never install dependencies")
    prefix = subprocess.check_output([brew, "--prefix"], text=True).strip()
    gitleaks = Path(prefix) / "bin" / "gitleaks"
    if shutil.which(str(gitleaks)) is None:
        raise SystemExit("Missing Homebrew gitleaks; install explicitly with mise scripts:install")
    # Snapshot current work, including new non-ignored files. Never copy local secrets.
    paths = subprocess.check_output(
        ["jj", "file", "list", "-T", 'path ++ "\\0"'], cwd=REPO
    ).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="dotfiles-scan-") as directory:
        for name in filter(None, paths):
            source = REPO / name
            # Do not follow links into local, unversioned data.
            if source.is_symlink():
                continue
            target = Path(directory) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        tree = subprocess.run(
            [str(gitleaks), "dir", directory, "--redact"], cwd=REPO
        ).returncode
    history = subprocess.run(
        [str(gitleaks), "git", ".", "--redact"], cwd=REPO
    ).returncode
    return tree or history


if __name__ == "__main__":
    raise SystemExit(main())
