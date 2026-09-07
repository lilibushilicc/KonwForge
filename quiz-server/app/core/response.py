"""统一响应：/api/v1 下 2xx 的 JSON 响应包成 {code:0, message:"ok", data:...}。

用中间件而不是自定义 APIRoute：FastAPI 0.141 起 include_router 改为延迟构造路由
（_IncludedRouter），子路由上的 route_class 会被丢弃，中间件则与版本无关。

业务 handler 只返回数据本体，OpenAPI 里 response_model 因此仍是精确形状。
异常响应由 core/exceptions.py 直接产出信封，中间件检测到即跳过。
"""

import json

from starlette.requests import Request
from starlette.responses import Response

_ENVELOPE_KEYS = {"code", "message", "data"}
_DROP_HEADERS = {"content-length", "content-type"}


def envelope_error(code: int, message: str, extra: dict | None = None) -> dict:
    """错误响应体：保持 {code, message, data} 结构，data 承载附加字段。"""
    return {"code": code, "message": message, "data": extra or {}}


def make_envelope_middleware(prefix: str):
    async def envelope_middleware(request: Request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if not request.url.path.startswith(prefix):
            return response
        if "application/json" not in content_type:
            return response
        if not 200 <= response.status_code < 300:
            return response  # 错误响应已由异常处理器包成信封

        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=content_type,
            )

        headers = {k: v for k, v in response.headers.items() if k.lower() not in _DROP_HEADERS}
        if isinstance(payload, dict) and _ENVELOPE_KEYS.issubset(payload.keys()):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=content_type,
            )

        wrapped = json.dumps(
            {"code": 0, "message": "ok", "data": payload}, ensure_ascii=False
        ).encode("utf-8")
        return Response(
            content=wrapped,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )

    return envelope_middleware
