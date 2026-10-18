#!/usr/bin/env python3
#MISE description="显示 mise 任务文件、PWD 和原始工作目录"

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    print(f"PYTHON_FILE={Path(__file__).resolve()}")
    print(f"MISE_TASK_FILE={os.environ.get('MISE_TASK_FILE', '')}")
    print(f"PWD={Path.cwd()}")
    print(f"MISE_ORIGINAL_CWD={os.environ.get('MISE_ORIGINAL_CWD', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
