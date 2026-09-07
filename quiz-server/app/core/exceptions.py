"""领域异常 + 全局异常处理器。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from app.core.response import envelope_error


class AppError(Exception):
    """业务异常基类。"""

    status_code = status.HTTP_400_BAD_REQUEST
    message = "请求失败"

    def __init__(self, message: str | None = None, **extra):
        self.message = message or self.message
        self.extra = extra
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "资源不存在"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    message = "资源冲突"


class UnsupportedQuestionType(AppError):
    # starlette >= 1.6  renamed HTTP_422_UNPROCESSABLE_ENTITY
    status_code = (
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", None)
        or status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    message = "暂不支持的题型"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope_error(exc.status_code, exc.message, exc.extra),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 生产环境不应回传堆栈，DEBUG 下保留原文方便排障
        detail = str(exc) if getattr(app.state, "debug", False) else "服务器内部错误"
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(status_code=code, content=envelope_error(code, detail))
