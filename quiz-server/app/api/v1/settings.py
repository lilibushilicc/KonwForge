"""全局设置只读接口：供前端「设置」页展示部署侧配置（沙箱开关等）。

这些值来自部署环境 .env（只读）；前端不能运行时修改，修改需在部署环境改
.env 后重启。返回给前端的均为脱敏/纯展示字段。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", summary="读取全局配置（只读展示用）")
def get_settings():
    return {
        "sandbox_enabled": settings.SANDBOX_ENABLED,
        "sandbox_image": settings.SANDBOX_IMAGE,
        "sandbox_timeout_ms": settings.SANDBOX_TIMEOUT_MS,
        "sandbox_memory_mb": settings.SANDBOX_MEMORY_MB,
        "clear_streak": settings.CLEAR_STREAK,
        "heartbeat_timeout_sec": settings.HEARTBEAT_TIMEOUT_SEC,
        "debug": settings.DEBUG,
        "app_name": settings.APP_NAME,
        "writable": False,  # 当前为部署侧只读配置，前端仅展示
    }
