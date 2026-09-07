import { useMemo } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  TreeSelect,
  Typography,
  App,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../../components/common/PageHeader";
import { DifficultyTag } from "../../components/common/DifficultyTag";
import { questionsApi } from "../../api/questions";
import { categoriesApi, tagsApi } from "../../api/categories";
import { useBankStore, TYPE_LABELS, DIFFICULTY_OPTIONS } from "../../stores/bankStore";
import type { ListQuery, Question, QuestionStatus } from "../../types/question";
import { buildCategoryTree } from "../../utils/category";

const ORDER_OPTIONS = [
  { value: "created_at", label: "创建时间" },
  { value: "updated_at", label: "更新时间" },
  { value: "difficulty", label: "难度" },
  { value: "code", label: "编号" },
];

function fmtDate(s?: string | null) {
  if (!s) return "-";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString("zh-CN", { hour12: false });
}

export default function QuestionList() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { filters, setFilters, resetFilters, selectedRowKeys, setSelected } = useBankStore();

  // 「全部」status：把 status 置 undefined 即可
  const liveStatus = (filters.status as string) === "archived" ? "archived" : undefined;
  const query: ListQuery = { ...filters, status: liveStatus as QuestionStatus | undefined };

  const { data, isLoading } = useQuery({
    queryKey: ["questions", query],
    queryFn: () => questionsApi.list(query),
    placeholderData: (prev) => prev,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  });
  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: tagsApi.list,
  });

  const categoryTree = useMemo(() => buildCategoryTree(categories), [categories]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // 批量操作
  const batchMut = useMutation({
    mutationFn: (vars: { action: string; ids: number[]; payload?: Record<string, unknown> }) =>
      questionsApi.batch(vars.action, vars.ids, vars.payload ?? {}),
    onSuccess: (res, vars) => {
      message.success(`批量${labelOf(vars.action)}完成，共 ${res.affected} 题`);
      setSelected([]);
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e: any) => message.error(e?.message ?? "批量操作失败"),
  });

  const onDelete = useMutation({
    mutationFn: (id: number) => questionsApi.softDelete(id),
    onSuccess: () => {
      message.success("已归档");
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e: any) => message.error(e?.message ?? "删除失败"),
  });

  const setAndResetPage = (patch: Partial<ListQuery>) => setFilters({ ...patch, page: 1 });

  const columns: ColumnsType<Question> = [
    {
      title: "编号",
      dataIndex: "code",
      width: 110,
      render: (v: string) => <Typography.Text code>{v}</Typography.Text>,
    },
    {
      title: "题干",
      dataIndex: "stem",
      ellipsis: true,
      render: (v: string) => <span className="q-stem">{v}</span>,
    },
    {
      title: "题型",
      dataIndex: "type",
      width: 84,
      render: (v) => <Tag>{TYPE_LABELS[v as keyof typeof TYPE_LABELS]}</Tag>,
    },
    {
      title: "难度",
      dataIndex: "difficulty",
      width: 84,
      render: (v: number) => <DifficultyTag level={v} />,
    },
    {
      title: "分类",
      dataIndex: "category_name",
      width: 120,
      render: (v?: string | null) => v ?? <span className="muted">—</span>,
    },
    {
      title: "标签",
      dataIndex: "tags",
      width: 160,
      render: (tags: string[]) =>
        tags?.length ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <Tag key={t} color="blue">
                {t}
              </Tag>
            ))}
          </Space>
        ) : (
          <span className="muted">—</span>
        ),
    },
    {
      title: "更新",
      dataIndex: "updated_at",
      width: 160,
      render: fmtDate,
    },
    {
      title: "操作",
      key: "act",
      width: 130,
      render: (_, r) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => navigate(`/bank/${r.id}/edit`)}>
            编辑
          </Button>
          <Popconfirm title="归档该题？" onConfirm={() => onDelete.mutate(r.id)}>
            <Button type="link" size="small" danger>
              归档
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelected(keys as number[]),
  };

  return (
    <>
      <PageHeader
        title="题库"
        sub={`共 ${total} 题`}
        extra={
          <Space>
            <Button type="primary" onClick={() => navigate("/bank/new")}>
              新建题目
            </Button>
            <Button onClick={() => navigate("/bank/import")}>导入 / 导出</Button>
          </Space>
        }
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Form layout="inline" className="filter-form" style={{ gap: 8, flexWrap: "wrap" }}>
          <Form.Item label="关键词">
            <Input
              allowClear
              style={{ width: 200 }}
              placeholder="编号或题干"
              value={filters.keyword ?? ""}
              onChange={(e) => setFilters({ keyword: e.target.value })}
              onPressEnter={() => setAndResetPage({ keyword: filters.keyword })}
            />
          </Form.Item>
          <Form.Item label="题型">
            <Select
              mode="multiple"
              allowClear
              style={{ minWidth: 160 }}
              placeholder="全部"
              maxTagCount="responsive"
              value={filters.type ?? []}
              options={Object.entries(TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))}
              onChange={(v) => setAndResetPage({ type: v.length ? v : undefined })}
            />
          </Form.Item>
          <Form.Item label="分类">
            <TreeSelect
              allowClear
              style={{ minWidth: 180 }}
              placeholder="全部"
              treeData={categoryTree}
              treeDefaultExpandAll
              value={filters.category_id}
              onChange={(v) => setAndResetPage({ category_id: v ?? undefined })}
            />
          </Form.Item>
          <Form.Item label="难度">
            <Select
              mode="multiple"
              allowClear
              style={{ minWidth: 140 }}
              placeholder="全部"
              maxTagCount="responsive"
              value={filters.difficulty ?? []}
              options={DIFFICULTY_OPTIONS.map((d) => ({ value: d, label: `L${d}` }))}
              onChange={(v) => setAndResetPage({ difficulty: v.length ? v : undefined })}
            />
          </Form.Item>
          <Form.Item label="排序">
            <Select
              style={{ width: 120 }}
              value={filters.order_by}
              options={ORDER_OPTIONS}
              onChange={(v) => setAndResetPage({ order_by: v })}
            />
          </Form.Item>
          <Form.Item label="状态">
            <Segmented
              options={[
                { label: "有效", value: "active" },
                { label: "归档", value: "archived" },
                { label: "全部", value: "all" },
              ]}
              value={(filters.status === "archived" ? "archived" : filters.status) ?? "all"}
              onChange={(v) =>
                setAndResetPage({
                  status: v === "all" ? undefined : (v as QuestionStatus),
                })
              }
            />
          </Form.Item>
          <Form.Item>
            <Button onClick={resetFilters}>重置</Button>
          </Form.Item>
        </Form>
      </Card>

      {selectedRowKeys.length > 0 && (
        <BatchBar
          count={selectedRowKeys.length}
          categories={categories}
          tags={tags}
          onClear={() => setSelected([])}
          onRun={(action, payload) => batchMut.mutate({ action, ids: selectedRowKeys, payload })}
          loading={batchMut.isPending}
        />
      )}

      <Table<Question>
        rowKey="id"
        size="middle"
        loading={isLoading}
        scroll={{ x: 900 }}
        columns={columns}
        dataSource={items}
        rowSelection={rowSelection}
        pagination={{
          current: filters.page ?? 1,
          pageSize: filters.page_size ?? 20,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (page, pageSize) => setFilters({ page, page_size: pageSize }),
        }}
      />
    </>
  );
}

function labelOf(action: string) {
  return (
    { delete: "归档", set_category: "设分类", add_tags: "加标签", set_difficulty: "设难度" }[
      action
    ] ?? action
  );
}

function BatchBar({
  count,
  categories,
  tags,
  onClear,
  onRun,
  loading,
}: {
  count: number;
  categories: { id: number; name: string }[];
  tags: { id: number; name: string }[];
  onClear: () => void;
  onRun: (action: string, payload?: Record<string, unknown>) => void;
  loading: boolean;
}) {
  return (
      <Card
        size="small"
        style={{ marginBottom: 16, background: "var(--bg-soft)" }}
        bodyStyle={{ padding: "8px 12px" }}
      >
        <Space wrap className="batch-bar">
        <Typography.Text strong>已选 {count} 题</Typography.Text>
        <Popconfirm title={`归档所选 ${count} 题？`} onConfirm={() => onRun("delete")}>
          <Button size="small" danger loading={loading}>
            批量归档
          </Button>
        </Popconfirm>
        <Select
          size="small"
          style={{ width: 160 }}
          placeholder="设分类…"
          showSearch
          optionFilterProp="label"
          options={categories.map((c) => ({ value: c.id, label: c.name }))}
          onChange={(v) => onRun("set_category", { category_id: v })}
        />
        <Select
          size="small"
          mode="tags"
          style={{ minWidth: 180 }}
          placeholder="加标签…"
          tokenSeparators={[",", "，"]}
          options={tags.map((t) => ({ value: t.name, label: t.name }))}
          onChange={(v: string[]) => v.length && onRun("add_tags", { tags: v })}
        />
        <Select
          size="small"
          style={{ width: 100 }}
          placeholder="设难度…"
          options={[1, 2, 3, 4, 5].map((d) => ({ value: d, label: `L${d}` }))}
          onChange={(v) => onRun("set_difficulty", { difficulty: v })}
        />
        <Button size="small" type="link" onClick={onClear}>
          取消选择
        </Button>
      </Space>
    </Card>
  );
}
