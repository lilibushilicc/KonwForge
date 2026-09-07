from fastapi import APIRouter

from app.api.v1 import (
    categories,
    import_export,
    judge,
    mistakes,
    practice,
    questions,
    stats,
    tags,
)

router = APIRouter()
# 注册顺序有讲究：import_export 的 /questions/export、/questions/import 必须排在
# questions 的 /questions/{question_id} 之前，否则会被路径参数路由吞掉。
router.include_router(import_export.router)
router.include_router(questions.router)
router.include_router(categories.router)
router.include_router(tags.router)
router.include_router(judge.router)
router.include_router(practice.router)
router.include_router(mistakes.router)
router.include_router(stats.router)
