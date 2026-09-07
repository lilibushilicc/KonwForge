"""统计 API（M5），见 DESIGN §5.4。只读聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DbSession
from app.schemas.stats import StatsOut
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=StatsOut, summary="统计总览")
def summary(db: DbSession):
    return stats_service.get_stats(db)
