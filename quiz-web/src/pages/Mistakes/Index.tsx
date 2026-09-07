import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  Empty,
  Input,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  TreeSelect,
  Typography,
  App,
} from "antd";
import { RedoOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

import { PageHeader } from "../../components/common/PageHeader";
import { mistakesApi, type Mistake } from "../../api/mistakes";
import { categoriesApi } from "../../api/categories";
import type { Category } from "../../api/categories";
import { practiceApi } from "../../api/practice";

const TYPE_LABEL: Record<string, string> = {
  single_choice: "单选",
  multiple_choice: "多选",
  fill_blank: "填空",
  coding: "代码",
  essay: "简答",
};

function buildTree(cats: Category[]) {
  const map = new Map<number, any>();
  cats.forEach((c) => map.set(c.id, { ...c, title: c.name, value: c.id, key: c.id, children: [] }));
  const roots: any[] = [];
  map.forEach((n) => {
    if (n.parent_id && map.has(n.parent_id)) map.get(n.parent_id).children.push(n);
    else roots.push(n);
  });
  return roots;
}

export default function Mistakes() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState("");
  const [catId, setCatId] = useState<number>();
  const [onlyWrong, setOnlyWrong] = useState(false);
  const [mastered, setMastered] = useState<boolean | undefined>(undefined);

  const { data: cats = [] } = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const { data: list = [], isLoading } = useQuery({
    queryKey: ["mistakes", { keyword, catId, onlyWrong, mastered }],
    queryFn: () =>
      mistakesApi.list({
        keyword: keyword || undefined,
        category_id: catId,
        only_wrong: onlyWrong,
        mastered,
      }),
  });

  const patchMut = useMutation({
    mutationFn: ({ qid, d }: { qid: number; d: any }) => mistakesApi.update(qid, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mistakes"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const replayMut = useMutation({
    mutationFn: () => practiceApi.create({ mode: "mistake", count: 20 }),
    onSuccess: (s) => navigate(`/practice?session=${s.id}`),
    onError: () => message.warning("当前没有可重练的错题"),
  });

  const columns: ColumnsType<Mistake> = [
    {
      title: "题目",
      dataIndex: ["question", "stem"],
      render: (_v, r) => (
        <Space direction="vertical" size={2}>
          <Space>
            <Tag color="blue">{r.question.code}</Tag>
            <Tag>{TYPE_LABEL[r.question.type] ?? r.question.type}</Tag>
            {r.mastered && <Tag color="green">已掌握</Tag>}
          </Space>
          <Typography.Text ellipsis style={{ maxWidth: 520 }}>
            {r.question.stem}
          </Typography.Text>
        </Space>
      ),
    },
    { title: "分类", dataIndex: ["question", "category_name"], render: (v) => v || "—" },
    {
      title: "错/对",
      key: "wc",
      render: (_v, r) => (
        <Typography.Text>
          错 {r.wrong_count} · 对 {r.cleared_count}
        </Typography.Text>
      ),
    },
    {
      title: "操作",
      key: "act",
      render: (_v, r) => (
        <Space>
          <Button
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => patchMut.mutate({ qid: r.question_id, d: { removed: !r.removed } })}
          >
            {r.removed ? "恢复" : "移除"}
          </Button>
          <Popconfirm
            title="标记为已掌握？"
            onConfirm={() => patchMut.mutate({ qid: r.question_id, d: { mastered: !r.mastered } })}
          >
            <Button size="small" type={r.mastered ? "default" : "primary"}>
              {r.mastered ? "取消掌握" : "标记掌握"}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="错题本" sub="做错的题自动归集，可重练、标记掌握或移除" />
      <Card style={{ marginBottom: 16 }}>
        <Space wrap className="mistake-filter">
          <Input.Search
            placeholder="搜索题干"
            allowClear
            style={{ width: 220 }}
            onSearch={setKeyword}
            onChange={(e) => !e.target.value && setKeyword("")}
          />
          <TreeSelect
            allowClear
            placeholder="分类"
            style={{ width: 200 }}
            treeData={buildTree(cats)}
            treeDefaultExpandAll
            treeNodeFilterProp="title"
            showSearch
            value={catId}
            onChange={(v) => setCatId(v as number | undefined)}
          />
          <Select
            allowClear
            placeholder="掌握状态"
            style={{ width: 160 }}
            value={mastered}
            onChange={setMastered}
            options={[
              { value: true, label: "已掌握" },
              { value: false, label: "未掌握" },
            ]}
          />
          <Space>
            <Typography.Text type="secondary">仅看未掌握</Typography.Text>
            <Switch checked={onlyWrong} onChange={setOnlyWrong} />
          </Space>
          <Button
            type="primary"
            icon={<RedoOutlined />}
            loading={replayMut.isPending}
            onClick={() => replayMut.mutate()}
          >
            重练错题
          </Button>
        </Space>
      </Card>

      {list.length === 0 && !isLoading ? (
        <Empty description="暂无错题，去练习里制造几道吧" style={{ marginTop: 60 }} />
      ) : (
        <Table
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 680 }}
          columns={columns}
          dataSource={list}
          pagination={{ pageSize: 10 }}
        />
      )}
    </>
  );
}
