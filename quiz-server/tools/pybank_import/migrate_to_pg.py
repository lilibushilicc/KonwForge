"""把 SQLite 导出的快照迁移到 PostgreSQL。

前置：
  - 已 `uv run alembic upgrade head` 在 PG 建好表结构
  - 本脚本读取 out/categories_sqlite.json 与 out/export_sqlite.json

流程：
  1) 按 parent_id 顺序重建 24 个分类（保留根/章节父子关系）
  2) 调用应用层 import_json 灌入 600 题（自动建标签 + 建 QuestionStat）
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 让脚本能 import 到 app
sys.path.insert(0, str(HERE.parent.parent))

from app.db.session import SessionLocal
from app.models.category import Category
from app.services.import_export_service import import_json


def main() -> None:
    db = SessionLocal()

    cats = json.load(open(HERE / "out/categories_sqlite.json", encoding="utf-8"))
    data = json.load(open(HERE / "out/export_sqlite.json", encoding="utf-8"))

    # 1) 分类：保证父级先于子级创建（None 排前面）
    cats_sorted = sorted(cats, key=lambda c: (c["parent_id"] is not None, c["parent_id"] or 0))
    old_to_new: dict[int, int] = {}
    for c in cats_sorted:
        parent_new = old_to_new.get(c["parent_id"]) if c["parent_id"] else None
        obj = Category(name=c["name"], sort_order=c["sort_order"], parent_id=parent_new)
        db.add(obj)
        db.flush()
        old_to_new[c["id"]] = obj.id
    db.commit()
    print(f"[分类] 已重建 {len(old_to_new)} 个")

    # 2) 题目：import_json 按 category 名称解析 + 自动建标签 + 建统计行
    items = data["questions"]
    result = import_json(db, items, conflict="skip")
    print("[题目] 导入结果:", json.dumps(result, ensure_ascii=False))

    db.close()


if __name__ == "__main__":
    main()
