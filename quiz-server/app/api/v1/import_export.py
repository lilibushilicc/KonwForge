from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.deps import DbSession
from app.services import import_export_service as svc

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/export", summary="导出题目")
def export_questions(
    db: DbSession,
    fmt: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
):
    if fmt == "csv":
        csv_text = svc.export_csv(db)
        return PlainTextResponse(
            csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="questions.csv"'},
        )
    data = svc.export_json(db)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="questions.json"'},
    )


@router.post("/import", summary="导入题目（JSON）")
def import_questions(
    db: DbSession,
    payload: dict,
    conflict: Annotated[str, Query(pattern="^(skip|overwrite|rename)$")] = "skip",
):
    items = payload.get("questions")
    if not isinstance(items, list) or not items:
        from app.core.exceptions import ConflictError

        raise ConflictError("请求体需包含 questions 数组")
    return svc.import_json(db, items, conflict=conflict)
