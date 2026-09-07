"""M3/M4/M5 端到端冒烟：建会话 → 作答（写 attempt/stat/mistake）→ 交卷 → 错题 → 统计。"""

from conftest import unwrap

SINGLE = {
    "type": "single_choice",
    "stem": "单选题干",
    "difficulty": 2,
    "payload": {"options": [{"key": "A", "text": "甲"}, {"key": "B", "text": "乙"}]},
    "answer": {"correct": "B"},
    "judge_config": {},
}
MULTI = {
    "type": "multiple_choice",
    "stem": "多选题干",
    "difficulty": 3,
    "payload": {"options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}, {"key": "C", "text": "c"}]},
    "answer": {"correct": ["A", "B"]},
    "judge_config": {},
}
FILL = {
    "type": "fill_blank",
    "stem": "填空 ____ 测试",
    "difficulty": 2,
    "payload": {},
    "answer": {"blanks": [{"accepted": ["x", "X"]}]},
    "judge_config": {},
}
ESSAY = {
    "type": "essay",
    "stem": "简答题干",
    "difficulty": 3,
    "payload": {},
    "answer": {"reference": "要点", "keywords": ["要点"]},
    "judge_config": {},
}


def _seed(client):
    return [
        unwrap(client.post("/api/v1/questions", json=SINGLE)),
        unwrap(client.post("/api/v1/questions", json=MULTI)),
        unwrap(client.post("/api/v1/questions", json=FILL)),
        unwrap(client.post("/api/v1/questions", json=ESSAY)),
    ]


def test_practice_flow_writes_attempt_stat_mistake(client):
    qs = _seed(client)
    # 建会话：只抽单选+多选+填空（4 题里挑 3）
    body = {
        "mode": "practice",
        "count": 3,
        "filter": {"types": ["single_choice", "multiple_choice", "fill_blank"]},
    }
    sess = unwrap(client.post("/api/v1/practice/sessions", json=body))
    assert sess["total_count"] == 3
    assert len(sess["items"]) == 3

    items = sess["items"]
    # 单选：答对
    single_item = next(i for i in items if i["question"]["type"] == "single_choice")
    r1 = unwrap(client.post(
        f"/api/v1/practice/sessions/{sess['id']}/answer",
        json={"item_id": single_item["id"], "response": {"choice": "B"}},
    ))
    assert r1["correct"] is True
    assert r1["progress"]["answered"] == 1

    # 多选：答错（只选 A）
    multi_item = next(i for i in items if i["question"]["type"] == "multiple_choice")
    r2 = unwrap(client.post(
        f"/api/v1/practice/sessions/{sess['id']}/answer",
        json={"item_id": multi_item["id"], "response": {"choices": ["A"]}},
    ))
    assert r2["correct"] is False
    assert r2["reveal"]["answer"] == {"correct": ["A", "B"]}

    # 填空：答对
    fill_item = next(i for i in items if i["question"]["type"] == "fill_blank")
    unwrap(client.post(
        f"/api/v1/practice/sessions/{sess['id']}/answer",
        json={"item_id": fill_item["id"], "response": {"blanks": {"1": "x"}}},
    ))

    # 交卷
    res = unwrap(client.post(f"/api/v1/practice/sessions/{sess['id']}/submit"))
    assert res["correct_count"] == 2
    assert res["accuracy"] == 66.67

    # stat：单选那题 attempt_count=1, wrong=0
    q_single = next(q for q in qs if q["type"] == "single_choice")
    stat = unwrap(client.get(f"/api/v1/questions/{q_single['id']}"))["stat"]
    assert stat["attempt_count"] == 1
    assert stat["wrong_count"] == 0

    # mistake：多选那题应进错题本
    q_multi = next(q for q in qs if q["type"] == "multiple_choice")
    mistakes = unwrap(client.get("/api/v1/mistakes"))
    mids = {m["question_id"] for m in mistakes}
    assert q_multi["id"] in mids


def test_mistake_mark_mastered_and_removed(client):
    qs = _seed(client)
    q = qs[1]  # 多选
    # 先答错制造错题
    sess = unwrap(client.post("/api/v1/practice/sessions", json={
        "mode": "practice", "count": 1, "filter": {"types": ["multiple_choice"]},
    }))
    item = sess["items"][0]
    unwrap(client.post(
        f"/api/v1/practice/sessions/{sess['id']}/answer",
        json={"item_id": item["id"], "response": {"choices": ["C"]}},
    ))
    unwrap(client.post(f"/api/v1/practice/sessions/{sess['id']}/submit"))

    m = unwrap(client.get("/api/v1/mistakes"))[0]
    assert m["question_id"] == q["id"]
    assert m["mastered"] is False

    upd = unwrap(client.patch(f"/api/v1/mistakes/{q['id']}", json={"mastered": True}))
    assert upd["mastered"] is True

    # 软删后默认列表看不到
    unwrap(client.patch(f"/api/v1/mistakes/{q['id']}", json={"removed": True}))
    rest = unwrap(client.get("/api/v1/mistakes"))
    assert all(x["question_id"] != q["id"] for x in rest)
    # removed=true 能看到
    removed_list = unwrap(client.get("/api/v1/mistakes", params={"removed": "true"}))
    assert any(x["question_id"] == q["id"] for x in removed_list)


def test_stats_aggregates(client):
    _seed(client)
    # 跑一个会话制造 attempt / mistake
    sess = unwrap(client.post("/api/v1/practice/sessions", json={
        "mode": "practice", "count": 2, "filter": {"types": ["single_choice", "fill_blank"]},
    }))
    for it in sess["items"]:
        resp = {"choice": "B"} if it["question"]["type"] == "single_choice" else {"blanks": {"1": "x"}}
        unwrap(client.post(f"/api/v1/practice/sessions/{sess['id']}/answer", json={"item_id": it["id"], "response": resp}))
    unwrap(client.post(f"/api/v1/practice/sessions/{sess['id']}/submit"))

    stats = unwrap(client.get("/api/v1/stats/summary"))
    assert stats["summary"]["total_attempts"] == 2
    assert stats["summary"]["total_sessions"] == 1
    assert stats["summary"]["overall_accuracy"] == 100.0
    assert len(stats["by_type"]) >= 1
    assert len(stats["mastery"]) == 6  # 0..5
    assert len(stats["daily"]) == 30


def test_mistake_mode_session_only_picks_mistakes(client):
    qs = _seed(client)
    q_multi = qs[1]
    # 制造一个错题
    sess = unwrap(client.post("/api/v1/practice/sessions", json={
        "mode": "practice", "count": 1, "filter": {"types": ["multiple_choice"]},
    }))
    unwrap(client.post(
        f"/api/v1/practice/sessions/{sess['id']}/answer",
        json={"item_id": sess["items"][0]["id"], "response": {"choices": ["C"]}},
    ))
    unwrap(client.post(f"/api/v1/practice/sessions/{sess['id']}/submit"))

    # 错题模式建会话应只含该错题
    msess = unwrap(client.post("/api/v1/practice/sessions", json={"mode": "mistake", "count": 10}))
    assert msess["total_count"] == 1
    assert msess["items"][0]["question_id"] == q_multi["id"]


def test_category_mode_expands_descendants(client):
    """回归：选父分类建分类练习会话时，应展开到其下全部子分类的题目。"""
    root = unwrap(client.post("/api/v1/categories", json={"name": "回归测试根"}))
    child = unwrap(client.post("/api/v1/categories", json={"name": "回归测试子", "parent_id": root["id"]}))

    # 题只挂在叶子 child 下
    q1 = unwrap(client.post("/api/v1/questions", json={**SINGLE, "category_id": child["id"]}))
    q2 = unwrap(client.post("/api/v1/questions", json={**FILL, "category_id": child["id"]}))

    # 选 root（父分类）建分类练习会话：应展开到 child，拿到 2 题，且不再触发 count>200 的 422
    sess = unwrap(client.post("/api/v1/practice/sessions", json={
        "mode": "category",
        "filter": {"category_ids": [root["id"]]},
    }))
    assert sess["total_count"] == 2
    got = {i["question_id"] for i in sess["items"]}
    assert got == {q1["id"], q2["id"]}
