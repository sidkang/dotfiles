#!/usr/bin/env python3
"""Save, check, restore, or apply one file using age and shared recipients."""

import argparse
import difflib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]


def age(args, data=None):
    # Neither decrypted contents nor plugin errors may be echoed into logs.
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError("age failed; check identities, recipients, plugins and authentication")
    return result.stdout


def identity(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("identity must be a regular file outside the repository")
    if REPO == path.resolve() or REPO in path.resolve().parents:
        raise RuntimeError("identity must stay outside the repository")
    if path.stat().st_mode & 0o077:
        raise RuntimeError("identity permissions must be 0600 or stricter")
    return path


def read_file(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("expected a regular file, not a symlink")
    return path.read_bytes()


def decrypt(archive, key):
    read_file(archive)
    return age(["age", "--decrypt", "--identity", str(key), str(archive)])


def save(source, archive, key, recipients, reencrypt):
    data = read_file(source)
    recipient_data = read_file(recipients)
    if not any(line.strip() and not line.lstrip().startswith(b"#")
               for line in recipient_data.splitlines()):
        raise RuntimeError("recipient list is empty; add all intended recipients first")
    if archive.exists() and not reencrypt and decrypt(archive, key) == data:
        print("Already saved; ciphertext unchanged.")
        return
    if archive.is_symlink():
        raise RuntimeError("refusing a symlink at the encrypted output")
    encrypted = age(["age", "--encrypt", "--armor", "--recipients-file", str(recipients)], data)
    if age(["age", "--decrypt", "--identity", str(key)], encrypted) != data:
        raise RuntimeError("round-trip verification failed; ciphertext not saved")
    if read_file(source) != data or read_file(recipients) != recipient_data:
        raise RuntimeError("source or recipients changed during encryption; retry")
    fd, temp = tempfile.mkstemp(prefix=".age-save-", dir=archive.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(encrypted)
        os.replace(temp, archive)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print("Encrypted file saved and verified; source unchanged.")


def check(source, archive, key):
    if decrypt(archive, key) != read_file(source):
        raise RuntimeError("source differs from encrypted file; use apply for archive -> local, or save for local -> archive")
    print("Source matches encrypted file.")


def restore(target, archive, key):
    data = decrypt(archive, key)
    if target.is_symlink():
        raise RuntimeError("refusing to replace a symlink")
    if target.exists():
        if read_file(target) != data:
            raise RuntimeError("existing target differs; refusing to overwrite it")
        print("Target already matches; no files changed.")
        return
    parent = target.parent
    if parent.is_symlink():
        raise RuntimeError("refusing a symlinked target directory")
    if not parent.exists():
        parent.mkdir(parents=True, mode=0o700)
    if not parent.is_dir() or parent.stat().st_mode & 0o077:
        raise RuntimeError("target directory permissions must be 0700 or stricter")
    fd, temp = tempfile.mkstemp(prefix=".age-restore-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        os.link(temp, target)  # Atomic no-clobber install, including concurrent writers.
    finally:
        os.unlink(temp)
    print("Restored regular file with permissions 0600.")


def preview_changes(current, incoming):
    """Show line ranges only; never expose configuration values or comments."""
    before = current.decode("utf-8", errors="replace").splitlines(keepends=True)
    after = incoming.decode("utf-8", errors="replace").splitlines(keepends=True)
    print("Changes: local -> archive (contents hidden)")
    for tag, start, end, new_start, new_end in difflib.SequenceMatcher(
            a=before, b=after, autojunk=False).get_opcodes():
        if tag != "equal":
            print(f"  {tag}: local line {start + 1} -> archive line {new_start + 1} "
                  f"(-{end - start}/+{new_end - new_start} lines)")


def apply(target, archive, key, *, yes=False, dry_run=False):
    """Decrypt once, preview, confirm, atomically apply and verify in memory."""
    if target.is_symlink():
        raise RuntimeError("refusing to replace a symlink")
    if target.parent.is_symlink():
        raise RuntimeError("refusing a symlinked target directory")
    if REPO == target.resolve() or REPO in target.resolve().parents:
        raise RuntimeError("plaintext target must stay outside the repository")
    if target.parent.exists() and (
            not target.parent.is_dir() or target.parent.stat().st_mode & 0o077):
        raise RuntimeError("target directory permissions must be 0700 or stricter")
    if not yes and not dry_run and not sys.stdin.isatty():
        raise RuntimeError("confirmation requires a terminal; use --yes only after explicit approval")
    current = read_file(target) if target.exists() else None
    encrypted = read_file(archive)
    # Keep the exact ciphertext and plaintext in memory for the entire operation.
    data = age(["age", "--decrypt", "--identity", str(key)], encrypted)
    if current == data:
        print("Target already matches; no files changed.")
        return
    preview_changes(current or b"", data)
    if dry_run:
        print("Preview only; no files changed.")
        return
    if not yes:
        try:
            answer = input("Apply archive to local file without a backup? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in {"y", "yes"}:
            print("Cancelled; no files changed.")
            return
    # Do not overwrite edits made while decryption or confirmation was pending.
    if target.is_symlink() or target.parent.is_symlink():
        raise RuntimeError("target path changed; nothing applied")
    latest = read_file(target) if target.exists() else None
    if latest != current or read_file(archive) != encrypted:
        raise RuntimeError("local file or archive changed; nothing applied")
    parent = target.parent
    if not parent.exists():
        parent.mkdir(parents=True, mode=0o700)
    if not parent.is_dir() or parent.stat().st_mode & 0o077:
        raise RuntimeError("target directory permissions must be 0700 or stricter")
    fd, temp = tempfile.mkstemp(prefix=".age-apply-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if current is None:
            os.link(temp, target)  # Refuse a concurrent creation.
        else:
            os.replace(temp, target)
        if read_file(target) != data:
            raise RuntimeError("target changed during verification")
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print("Applied and verified against decrypted archive (0600); no backup created.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["save", "check", "restore", "apply"])
    parser.add_argument("--file", required=True, type=Path, help="plaintext source or restore target")
    parser.add_argument("--encrypted", required=True, type=Path, help="age ciphertext path")
    parser.add_argument("--recipients", type=Path, default=REPO / "age/recipients.txt")
    parser.add_argument("--identity", type=Path,
                        default=Path(os.environ.get("SOPS_AGE_KEY_FILE", "~/.config/sops/age/keys.txt")).expanduser())
    parser.add_argument("--reencrypt", action="store_true", help="save even if plaintext is unchanged (recipient changes)")
    parser.add_argument("--yes", action="store_true", help="apply without an interactive confirmation")
    parser.add_argument("--dry-run", action="store_true", help="apply: preview only; do not write")
    args = parser.parse_args()
    try:
        if args.file.resolve() == args.encrypted.resolve():
            raise RuntimeError("plaintext and ciphertext must be different paths")
        if args.reencrypt and args.action != "save":
            raise RuntimeError("--reencrypt is only valid with save")
        if (args.yes or args.dry_run) and args.action != "apply":
            raise RuntimeError("--yes and --dry-run are only valid with apply")
        key = identity(args.identity.expanduser())
        if args.action == "save":
            save(args.file, args.encrypted, key, args.recipients, args.reencrypt)
        elif args.action == "check":
            check(args.file, args.encrypted, key)
        elif args.action == "restore":
            restore(args.file, args.encrypted, key)
        else:
            apply(args.file, args.encrypted, key, yes=args.yes, dry_run=args.dry_run)
    except (OSError, RuntimeError) as error:
        print("age-file: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
