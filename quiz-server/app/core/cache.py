"""进程内 TTL 缓存：只用于「低频写、高频读」的配置型数据（分类 / 标签 / 统计）。

跨区数据库（如 Turso 东京区）场景下每条 SQL 都是一次跨洋往返（~30-70ms），
分类树 / 标签列表 / 统计总览这类基本不变的数据缓存 60s，可把接口从
数十次 RTT 压到内存命中（<1ms）。

失效策略：任何写路径（题目 / 分类 / 标签 / 作答 / 导入）统一 invalidate_all()，
粗暴但正确——写本来就低频，不值得做键级精细失效。
"""

from __future__ import annotations

import functools
import threading
import time

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, object]] = {}

DEFAULT_TTL = 60.0
STATS_TTL = 30.0  # 统计随作答变化，缓存窗口短一些


def get(key: str):
    with _LOCK:
        hit = _STORE.get(key)
        if hit is None:
            return None
        expires_at, value = hit
        if time.monotonic() > expires_at:
            _STORE.pop(key, None)
            return None
        return value


def set(key: str, value, ttl: float = DEFAULT_TTL) -> None:
    with _LOCK:
        _STORE[key] = (time.monotonic() + ttl, value)


def invalidate_all() -> None:
    with _LOCK:
        _STORE.clear()


def cached(key: str, ttl: float = DEFAULT_TTL):
    """装饰器：函数返回值按 key 缓存 ttl 秒。只用于无参或参数无关全局的读函数。"""

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            hit = get(key)
            if hit is not None:
                return hit
            value = fn(*args, **kwargs)
            set(key, value, ttl)
            return value

        return wrapper

    return deco


def invalidates_cache(fn):
    """装饰器：写函数执行成功后清空全部缓存。"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        invalidate_all()
        return result

    return wrapper
