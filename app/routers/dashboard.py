"""Server-sent events dashboard metrics."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import socket
from collections.abc import AsyncIterator

import psutil
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..config import BASE_DIR
from ..deps import current_user

router = APIRouter(prefix="/admin", dependencies=[Depends(current_user)])


def _size(value: float) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def _snapshot() -> dict:
    memory = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage("/")
    except OSError:
        disk = psutil.disk_usage(os.path.abspath(os.sep))
    return {
        "ProjectVersion": "python-1.0",
        "GoOS": platform.system(),
        "GoArch": platform.machine(),
        "GoVersion": f"Python {platform.python_version()}",
        "ProjectPath": str(BASE_DIR),
        "Host": socket.gethostname(),
        "Env": os.getenv("WEBSTACK_ENV", "development"),
        "MemTotal": _size(memory.total),
        "MemUsed": _size(memory.used),
        "MemUsedPercent": round(float(memory.percent), 1),
        "DiskTotal": _size(disk.total),
        "DiskUsed": _size(disk.used),
        "DiskUsedPercent": round(float(disk.percent), 1),
        "CpuName": platform.processor() or "unknown",
        "CpuCores": psutil.cpu_count(logical=True) or 0,
        "CpuUsedPercent": round(float(psutil.cpu_percent(interval=None)), 1),
    }


async def _events(request: Request) -> AsyncIterator[str]:
    psutil.cpu_percent(interval=None)  # prime the non-blocking sampler
    yield f"event: dashboard\ndata: {json.dumps(_snapshot(), ensure_ascii=False)}\n\n"
    while True:
        if await request.is_disconnected():
            break
        await asyncio.sleep(1)
        yield f"event: dashboard\ndata: {json.dumps(_snapshot(), ensure_ascii=False)}\n\n"


@router.get("/dashboard")
async def dashboard(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
