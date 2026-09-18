from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_local_env(path: str | Path) -> bool:
    """加载未跟踪的本地环境文件，不覆盖调用进程已经设置的变量。"""
    return load_dotenv(dotenv_path=Path(path), override=False)
