"""Synthetic SSH fixtures only; never invoke age or read real identities."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("age_file", Path(__file__).with_name("age-file.py"))
age_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(age_file)


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "ssh/config"
        self.target.parent.mkdir(mode=0o700)
        self.original = b"Host synthetic-old\n  HostName private-old.invalid\n"
        self.incoming = self.original + b"Host synthetic-new\n  User private-user\n"
        self.target.write_bytes(self.original)
        self.target.chmod(0o600)
        self.archive = self.root / "config.age"
        self.archive.write_bytes(b"synthetic ciphertext")
        self.key = self.root / "identity"
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.decrypt = patch.object(age_file, "age", return_value=self.incoming).start()
        self.addCleanup(patch.stopall)

    def apply(self, **kwargs):
        age_file.apply(self.target, self.archive, self.key, **kwargs)

    def assert_one_decryption(self):
        self.decrypt.assert_called_once_with(
            ["age", "--decrypt", "--identity", str(self.key)], b"synthetic ciphertext"
        )

    def assert_no_extra_files(self):
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_apply_once_verifies_and_leaves_no_backup(self):
        self.apply(yes=True)
        self.assertEqual(self.target.read_bytes(), self.incoming)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.archive.read_bytes(), b"synthetic ciphertext")
        self.assert_one_decryption()
        self.assert_no_extra_files()
        self.assertIn("Applied and verified", self.output.getvalue())
        for private in ("synthetic-old", "synthetic-new", "private-old", "private-user"):
            self.assertNotIn(private, self.output.getvalue())

    def test_preview_does_not_write(self):
        self.apply(dry_run=True)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_one_decryption()
        self.assert_no_extra_files()
        self.assertIn("-0/+2", self.output.getvalue())

    def test_identical_content_is_not_rewritten(self):
        self.decrypt.return_value = self.original
        before = self.target.stat()
        self.apply(yes=True)
        self.assertEqual(self.target.stat().st_ino, before.st_ino)
        self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)
        self.assert_one_decryption()

    def test_accept_confirmation(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="y"):
            self.apply()
        self.assertEqual(self.target.read_bytes(), self.incoming)
        self.assert_one_decryption()

    def test_decline_confirmation(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="n"):
            self.apply()
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_one_decryption()
        self.assert_no_extra_files()

    def test_confirmation_eof_cancels(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=EOFError):
            self.apply()
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_one_decryption()

    def test_noninteractive_requires_explicit_yes(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "confirmation requires"):
                self.apply()
        self.decrypt.assert_not_called()
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_no_extra_files()

    def test_missing_target_created_securely(self):
        self.target.unlink()
        self.target.parent.rmdir()
        self.apply(yes=True)
        self.assertEqual(self.target.read_bytes(), self.incoming)
        self.assertEqual(self.target.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assert_one_decryption()
        self.assert_no_extra_files()

    def test_symlink_refused_before_authentication(self):
        self.target.unlink()
        self.target.symlink_to(self.archive)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            self.apply(yes=True)
        self.decrypt.assert_not_called()

    def test_insecure_directory_refused_before_authentication(self):
        self.target.parent.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "0700"):
            self.apply(yes=True)
        self.decrypt.assert_not_called()

    def test_repository_target_refused_before_authentication(self):
        with patch.object(age_file, "REPO", self.root.resolve()):
            with self.assertRaisesRegex(RuntimeError, "outside the repository"):
                self.apply(yes=True)
        self.decrypt.assert_not_called()

    def test_edits_during_confirmation_are_preserved(self):
        def concurrent_edit(_):
            self.target.write_bytes(b"concurrent local edit")
            return "y"
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=concurrent_edit):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                self.apply()
        self.assertEqual(self.target.read_bytes(), b"concurrent local edit")
        self.assert_one_decryption()
        self.assert_no_extra_files()

    def test_archive_changed_during_confirmation_is_refused(self):
        def concurrent_edit(_):
            self.archive.write_bytes(b"different ciphertext")
            return "y"
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=concurrent_edit):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                self.apply()
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_one_decryption()

    def test_decryption_failure_does_not_write(self):
        self.decrypt.side_effect = RuntimeError("synthetic failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            self.apply(yes=True)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_no_extra_files()

    def test_replace_failure_cleans_up_temporary_file(self):
        with patch.object(os, "replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                self.apply(yes=True)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assert_no_extra_files()

    def test_task_entrypoint_with_fake_age_decrypts_once(self):
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake_age = fake_bin / "age"
        calls = self.root / "calls"
        fake_age.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "assert sys.argv[1] == '--decrypt'\n"
            "assert sys.stdin.buffer.read() == b'synthetic ciphertext'\n"
            "with Path(os.environ['TEST_AGE_CALLS']).open('a') as f: f.write('decrypt\\n')\n"
            f"sys.stdout.buffer.write({self.incoming!r})\n"
        )
        fake_age.chmod(0o700)
        self.key.write_bytes(b"synthetic identity")
        self.key.chmod(0o600)
        env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'],
                   TEST_AGE_CALLS=str(calls))
        env.pop("MISE_TASK_FILE", None)
        task = Path(__file__).resolve().parents[1] / "mise/tasks/ssh/apply"
        result = subprocess.run([
            sys.executable, str(task), "--file", str(self.target),
            "--encrypted", str(self.archive), "--identity", str(self.key), "--yes",
        ], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls.read_text(), "decrypt\n")
        self.assertEqual(self.target.read_bytes(), self.incoming)
        self.assertNotIn("private-user", result.stdout + result.stderr)
        self.assert_no_extra_files()

    def test_restore_still_refuses_overwrite(self):
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            age_file.restore(self.target, self.archive, self.key)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_main_rejects_apply_flags_for_save_before_authentication(self):
        for flag in ("--yes", "--dry-run"):
            with self.subTest(flag=flag), patch("sys.argv", [
                "age-file.py", "save", "--file", str(self.target),
                "--encrypted", str(self.archive), flag,
            ]), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(age_file.main(), 1)
        self.decrypt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
