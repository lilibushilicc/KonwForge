"""M1 冒烟：题库 / 分类 / 标签 CRUD + 统一响应信封。"""

from conftest import unwrap

SINGLE = {
    "type": "single_choice",
    "stem": "TCP 三次握手的第二步报文标志位是？",
    "analysis": "第二步是 SYN+ACK。",
    "difficulty": 3,
    "tags": ["网络", "TCP"],
    "payload": {"options": [{"key": "A", "text": "SYN"}, {"key": "B", "text": "SYN+ACK"}]},
    "answer": {"correct": "B"},
    "judge_config": {},
}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_and_get(client):
    created = unwrap(client.post("/api/v1/questions", json=SINGLE))
    assert created["code"].startswith("Q-")
    assert created["tags"] == ["网络", "TCP"]
    assert created["version"] == 1
    assert created["stat"]["attempt_count"] == 0

    got = unwrap(client.get(f"/api/v1/questions/{created['id']}"))
    assert got["stem"] == SINGLE["stem"]
    assert got["answer"] == {"correct": "B"}


def test_code_auto_increment(client):
    a = unwrap(client.post("/api/v1/questions", json=SINGLE))
    b = unwrap(client.post("/api/v1/questions", json=SINGLE))
    assert a["code"] != b["code"]


def test_update_bumps_version_only_on_payload_change(client):
    created = unwrap(client.post("/api/v1/questions", json=SINGLE))

    v1 = unwrap(client.patch(f"/api/v1/questions/{created['id']}", json={"difficulty": 5}))
    assert v1["difficulty"] == 5
    assert v1["version"] == 1  # 改非载荷字段不升版本

    v2 = unwrap(
        client.patch(
            f"/api/v1/questions/{created['id']}", json={"answer": {"correct": "A"}}
        )
    )
    assert v2["version"] == 2
    assert v2["answer"] == {"correct": "A"}


def test_list_filter_by_type_and_tag(client):
    client.post("/api/v1/questions", json=SINGLE)
    client.post(
        "/api/v1/questions",
        json={**SINGLE, "type": "essay", "tags": ["写作"], "stem": "谈谈索引设计"},
    )

    all_page = unwrap(client.get("/api/v1/questions"))
    assert all_page["total"] == 2

    only_single = unwrap(client.get("/api/v1/questions", params={"type": ["single_choice"]}))
    assert only_single["total"] == 1
    assert only_single["items"][0]["type"] == "single_choice"

    by_keyword = unwrap(client.get("/api/v1/questions", params={"keyword": "三次握手"}))
    assert by_keyword["total"] == 1

    tags = unwrap(client.get("/api/v1/tags"))
    tag_id = next(t["id"] for t in tags if t["name"] == "TCP")
    filtered = unwrap(client.get("/api/v1/questions", params={"tag_ids": [tag_id]}))
    assert filtered["total"] == 1


def test_soft_delete_hides_from_default_list(client):
    created = unwrap(client.post("/api/v1/questions", json=SINGLE))
    unwrap(client.delete(f"/api/v1/questions/{created['id']}"))

    assert unwrap(client.get("/api/v1/questions"))["total"] == 0
    archived = unwrap(client.get("/api/v1/questions", params={"status": "archived"}))
    assert archived["total"] == 1


def test_hard_delete(client):
    created = unwrap(client.post("/api/v1/questions", json=SINGLE))
    unwrap(client.delete(f"/api/v1/questions/{created['id']}/hard"))
    assert client.get(f"/api/v1/questions/{created['id']}").status_code == 404


def test_category_tree_and_contains_children(client):
    root = unwrap(client.post("/api/v1/categories", json={"name": "数据库"}))
    child = unwrap(client.post("/api/v1/categories", json={"name": "索引", "parent_id": root["id"]}))

    client.post("/api/v1/questions", json={**SINGLE, "category_id": child["id"]})

    hit = unwrap(client.get("/api/v1/questions", params={"category_id": root["id"]}))
    assert hit["total"] == 1  # 父分类能筛到子分类下的题

    unwrap(client.delete(f"/api/v1/categories/{root['id']}"))
    promoted = unwrap(client.get("/api/v1/categories"))
    assert [c["name"] for c in promoted] == ["索引"]
    assert promoted[0]["parent_id"] is None


def test_batch_set_difficulty(client):
    ids = [
        unwrap(client.post("/api/v1/questions", json=SINGLE))["id"],
        unwrap(client.post("/api/v1/questions", json=SINGLE))["id"],
    ]
    result = unwrap(
        client.post(
            "/api/v1/questions/batch",
            json={"action": "set_difficulty", "ids": ids, "payload": {"difficulty": 5}},
        )
    )
    assert result["affected"] == 2
    page = unwrap(client.get("/api/v1/questions", params={"difficulty": [5]}))
    assert page["total"] == 2


def test_error_envelope(client):
    resp = client.get("/api/v1/questions/9999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert "不存在" in body["message"]
