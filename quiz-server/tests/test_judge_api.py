"""/judge/preview 与 /judge/essay/self 冒烟。"""

from conftest import unwrap

SINGLE = {
    "type": "single_choice",
    "stem": "TCP 三次握手的第二步标志位是？",
    "difficulty": 3,
    "tags": ["网络"],
    "payload": {"options": [{"key": "A", "text": "SYN"}, {"key": "B", "text": "SYN+ACK"}]},
    "answer": {"correct": "B"},
    "judge_config": {},
}

ESSAY = {
    "type": "essay",
    "stem": "简述 TCP 三次握手",
    "difficulty": 3,
    "tags": [],
    "payload": {},
    "answer": {"reference": "三次握手用于建立 TCP 连接", "keywords": ["TCP", "握手"]},
    "judge_config": {},
}


def test_judge_preview_correct(client):
    q = unwrap(client.post("/api/v1/questions", json=SINGLE))
    r = unwrap(
        client.post(
            "/api/v1/judge/preview",
            json={"question_id": q["id"], "response": {"choice": "B"}, "max_score": 2.0},
        )
    )
    assert r["is_correct"] is True
    assert r["score"] == 2.0
    assert r["max_score"] == 2.0


def test_judge_preview_wrong(client):
    q = unwrap(client.post("/api/v1/questions", json=SINGLE))
    r = unwrap(
        client.post(
            "/api/v1/judge/preview",
            json={"question_id": q["id"], "response": {"choice": "A"}},
        )
    )
    assert r["is_correct"] is False and r["score"] == 0.0


def test_judge_preview_essay_manual(client):
    q = unwrap(client.post("/api/v1/questions", json=ESSAY))
    r = unwrap(
        client.post(
            "/api/v1/judge/preview",
            json={"question_id": q["id"], "response": {"text": "TCP 三次握手建立连接"}},
        )
    )
    assert r["need_manual"] is True
    assert r["is_correct"] is None
    assert r["detail"]["coverage"] == 1.0


def test_judge_preview_unknown_question(client):
    # 不存在的题目 → 404 信封
    resp = client.post("/api/v1/judge/preview", json={"question_id": 9999, "response": {}})
    body = resp.json()
    assert body["code"] != 0 and resp.status_code == 404


def test_essay_self_eval(client):
    for level, expect in [("mastered", False), ("fuzzy", True), ("unknown", True)]:
        r = unwrap(
            client.post(
                "/api/v1/judge/essay/self",
                json={"question_id": 1, "response": {"text": "..."}, "level": level},
            )
        )
        assert r["level"] == level and r["need_review"] is expect
