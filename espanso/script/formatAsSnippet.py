import subprocess
import sys


def read_from_clipboard():
    return subprocess.check_output(["pbpaste"], env={"LANG": "en_US.UTF-8"}).decode(
        "utf-8"
    )


text = read_from_clipboard()

sys.stdout.write(repr(text))
