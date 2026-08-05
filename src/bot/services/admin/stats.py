from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psutil
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import payment as payment_repo
from bot.db.repositories.user import count_active_since, count_all

# "Онлайн" = активны за последние ONLINE_WINDOW_HOURS часов (User.last_active_at) —
# у long-polling бота нет понятия текущего подключения, см. CLAUDE.md, "Админ-панель".
ONLINE_WINDOW_HOURS = 24


@dataclass
class ServerStats:
    cpu_percent: float
    ram_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


@dataclass
class AdminStats:
    total_users: int
    online_users: int
    payments_count: int
    payments_rub: int
    server: ServerStats


def _read_server_stats() -> ServerStats:
    """psutil делает блокирующие syscalls — вызывать только через asyncio.to_thread
    (см. CLAUDE.md, правило 5: никаких блокирующих вызовов в event loop)."""
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return ServerStats(
        cpu_percent=cpu,
        ram_percent=mem.percent,
        ram_used_mb=mem.used // (1024 * 1024),
        ram_total_mb=mem.total // (1024 * 1024),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / (1024**3), 1),
        disk_total_gb=round(disk.total / (1024**3), 1),
    )


async def get_stats(session: AsyncSession) -> AdminStats:
    total_users = await count_all(session)
    since = datetime.now(timezone.utc) - timedelta(hours=ONLINE_WINDOW_HOURS)
    online_users = await count_active_since(session, since)
    payments_rub, payments_count = await payment_repo.get_totals(session)
    server = await asyncio.to_thread(_read_server_stats)

    return AdminStats(
        total_users=total_users,
        online_users=online_users,
        payments_count=payments_count,
        payments_rub=payments_rub,
        server=server,
    )
