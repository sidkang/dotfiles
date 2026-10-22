#!/usr/bin/env python3
"""Save, check, or safely restore one file using age and shared recipients."""

import argparse
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
        raise RuntimeError("source differs from encrypted file; save it explicitly")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["save", "check", "restore"])
    parser.add_argument("--file", required=True, type=Path, help="plaintext source or restore target")
    parser.add_argument("--encrypted", required=True, type=Path, help="age ciphertext path")
    parser.add_argument("--recipients", type=Path, default=REPO / "age/recipients.txt")
    parser.add_argument("--identity", type=Path,
                        default=Path(os.environ.get("SOPS_AGE_KEY_FILE", "~/.config/sops/age/keys.txt")).expanduser())
    parser.add_argument("--reencrypt", action="store_true", help="save even if plaintext is unchanged (recipient changes)")
    args = parser.parse_args()
    try:
        if args.file.resolve() == args.encrypted.resolve():
            raise RuntimeError("plaintext and ciphertext must be different paths")
        if args.reencrypt and args.action != "save":
            raise RuntimeError("--reencrypt is only valid with save")
        key = identity(args.identity.expanduser())
        if args.action == "save":
            save(args.file, args.encrypted, key, args.recipients, args.reencrypt)
        elif args.action == "check":
            check(args.file, args.encrypted, key)
        else:
            restore(args.file, args.encrypted, key)
    except (OSError, RuntimeError) as error:
        print("age-file: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
