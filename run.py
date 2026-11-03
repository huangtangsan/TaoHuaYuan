"""本地启动脚本：python run.py

默认监听 127.0.0.1:8300。
不直接用 8000 是因为部分 Windows 环境上该端口会被系统保留或被高权限进程占用，
uvicorn 会直接抛 WinError 10013/10048；如确认可用，可用 WEBSTACK_PORT=8000 覆盖。
"""

import os
import sys

HOST = os.getenv("WEBSTACK_HOST", "127.0.0.1")
PORT = int(os.getenv("WEBSTACK_PORT", "8300"))
RELOAD = os.getenv("WEBSTACK_RELOAD", "1") == "1"

REBUILD_HINT = (
    "当前虚拟环境与 Python 版本不匹配（通常是 .venv 建好后换了 Python 版本）。\n"
    "Windows 下重建：\n"
    "  rmdir /s /q .venv\n"
    "  python -m venv .venv\n"
    "  .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
    "requirements.txt 已按当前 Python 版本适配（3.13 / 3.14 均已验证），不要手工降级依赖。"
)


def preflight() -> None:
    """Check the compiled dependencies early, before uvicorn forks.

    uvicorn 的 reload 模式会在子进程里导入应用，报错栈会沉在子进程里很难定位；
    这里先导入一次，把环境问题和业务报错分开。
    """
    try:
        import pydantic_core  # noqa: F401
        from PIL import Image  # noqa: F401
        import psutil  # noqa: F401

        import app.main  # noqa: F401
    except ImportError as exc:  # pragma: no cover - 只在环境损坏时触发
        name = getattr(exc, "name", "") or ""
        compiled = ("pydantic_core", "PIL", "_imaging", "psutil", "yaml", "httptools")
        print(f"\n[启动失败] 无法导入 {name or exc}\n", file=sys.stderr)
        if any(item.split(".")[0] in (name or "") for item in compiled) or "_pydantic_core" in str(exc):
            print(REBUILD_HINT, file=sys.stderr)
        else:
            print(f"原始错误：{exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    preflight()
    import uvicorn

    print(f"Python {sys.version.split()[0]} | http://{HOST}:{PORT}")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
