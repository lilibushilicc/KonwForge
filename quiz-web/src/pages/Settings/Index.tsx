import { useMemo, useState } from "react";
import {
  App,
  Button,
  Card,
  Col,
  ColorPicker,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Space,
  Table,
  Tag as AntTag,
  Tooltip,
  Tree,
} from "antd";
import type { DataNode } from "antd/es/tree";
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../../components/common/PageHeader";
import { categoriesApi, tagsApi } from "../../api/categories";
import type { Category, Tag } from "../../api/categories";

export default function Settings() {
  return (
    <>
      <PageHeader title="题库设置" sub="分类与标签的集中管理" />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <CategoryPanel />
        </Col>
        <Col xs={24} lg={12}>
          <TagPanel />
        </Col>
      </Row>
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* 分类面板                                                                    */
/* -------------------------------------------------------------------------- */

type CatModalState =
  | { mode: "closed" }
  | { mode: "create"; parent: Category | null }
  | { mode: "rename"; target: Category };

function siblingsOf(list: Category[], parentId: number | null | undefined): Category[] {
  return list
    .filter((c) => (c.parent_id ?? null) === (parentId ?? null))
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
}

function CategoryPanel() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [modal, setModal] = useState<CatModalState>({ mode: "closed" });
  const [form] = Form.useForm<{ name: string }>();

  const { data: list = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["categories"] });

  const createMut = useMutation({
    mutationFn: (v: { name: string; parent: Category | null }) =>
      categoriesApi.create({ name: v.name, parent_id: v.parent?.id ?? null }),
    onSuccess: () => {
      message.success("分类已创建");
      setModal({ mode: "closed" });
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const renameMut = useMutation({
    mutationFn: (v: { id: number; name: string }) => categoriesApi.update(v.id, { name: v.name }),
    onSuccess: () => {
      message.success("已重命名");
      setModal({ mode: "closed" });
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => categoriesApi.remove(id),
    onSuccess: () => {
      message.success("已删除（子分类上提一级，题目转为未分类）");
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  /** 上移/下移：先把同级分类的 sort_order 归一化为 0..n，再交换目标与相邻项。 */
  const moveMut = useMutation({
    mutationFn: async ({ id, dir }: { id: number; dir: -1 | 1 }) => {
      const target = list.find((c) => c.id === id);
      if (!target) return;
      const sibs = siblingsOf(list, target.parent_id);
      const idx = sibs.findIndex((c) => c.id === id);
      const other = sibs[idx + dir];
      if (!other) return;
      await Promise.all(sibs.map((c, i) => categoriesApi.update(c.id, { sort_order: i })));
      await Promise.all([
        categoriesApi.update(id, { sort_order: idx + dir }),
        categoriesApi.update(other.id, { sort_order: idx }),
      ]);
    },
    onSuccess: () => {
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const openModal = (state: Exclude<CatModalState, { mode: "closed" }>) => {
    form.setFieldsValue({ name: state.mode === "rename" ? state.target.name : "" });
    setModal(state);
  };

  const onModalOk = async () => {
    const { name } = await form.validateFields();
    if (modal.mode === "create") createMut.mutate({ name, parent: modal.parent });
    else if (modal.mode === "rename") renameMut.mutate({ id: modal.target.id, name });
  };

  const treeData = useMemo<DataNode[]>(() => {
    const build = (parentId: number | null): DataNode[] =>
      siblingsOf(list, parentId).map((c) => {
        const sibs = siblingsOf(list, parentId);
        const idx = sibs.findIndex((s) => s.id === c.id);
        return {
          key: c.id,
          title: (
            <span className="cat-node">
              <span>{c.name}</span>
              <span
                className="cat-actions"
                onClick={(e) => {
                  e.stopPropagation();
                }}
              >
                {idx > 0 && (
                  <ArrowUpOutlined onClick={() => moveMut.mutate({ id: c.id, dir: -1 })} />
                )}
                {idx < sibs.length - 1 && (
                  <ArrowDownOutlined onClick={() => moveMut.mutate({ id: c.id, dir: 1 })} />
                )}
                <Tooltip title="新增子分类">
                  <PlusOutlined onClick={() => openModal({ mode: "create", parent: c })} />
                </Tooltip>
                <Tooltip title="重命名">
                  <EditOutlined onClick={() => openModal({ mode: "rename", target: c })} />
                </Tooltip>
                <Popconfirm
                  title="删除该分类？"
                  description="子分类将上提一级，其下题目转为未分类"
                  onConfirm={() => deleteMut.mutate(c.id)}
                >
                  <DeleteOutlined />
                </Popconfirm>
              </span>
            </span>
          ),
          children: build(c.id),
        };
      });
    return build(null);
  }, [list, moveMut, deleteMut]);

  return (
    <Card
      size="small"
      title={`分类（${list.length}）`}
      extra={
        <Button
          size="small"
          icon={<PlusOutlined />}
          onClick={() => openModal({ mode: "create", parent: null })}
        >
          新建根分类
        </Button>
      }
    >
      {treeData.length ? (
        <Tree blockNode defaultExpandAll treeData={treeData} selectable={false} />
      ) : (
        <Empty description="暂无分类，点击右上角新建" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      <Modal
        title={
          modal.mode === "create"
            ? modal.parent
              ? `新增子分类（属于「${modal.parent.name}」）`
              : "新建根分类"
            : modal.mode === "rename"
              ? "重命名分类"
              : ""
        }
        open={modal.mode !== "closed"}
        onOk={onModalOk}
        onCancel={() => setModal({ mode: "closed" })}
        confirmLoading={createMut.isPending || renameMut.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, whitespace: true, message: "请输入名称" }]}
          >
            <Input maxLength={64} placeholder="如：计算机网络 / TCP" onPressEnter={onModalOk} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* 标签面板                                                                    */
/* -------------------------------------------------------------------------- */

function TagPanel() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<{ name: string; color: string }>();

  const { data: tags = [], isLoading } = useQuery({ queryKey: ["tags"], queryFn: tagsApi.list });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["tags"] });

  const createMut = useMutation({
    mutationFn: (v: { name: string; color: string }) =>
      tagsApi.create({ name: v.name, color: v.color || null }),
    onSuccess: () => {
      message.success("标签已创建");
      setOpen(false);
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const renameMut = useMutation({
    mutationFn: (v: { id: number; name: string }) => tagsApi.update(v.id, { name: v.name }),
    onSuccess: () => {
      message.success("已重命名");
      invalidate();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const colorMut = useMutation({
    mutationFn: (v: { id: number; color: string | null }) =>
      tagsApi.update(v.id, { color: v.color }),
    onError: (e: Error) => {
      message.error(e.message);
      invalidate();
    },
    onSuccess: invalidate,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => tagsApi.remove(id),
    onSuccess: () => {
      message.success("已删除");
      invalidate();
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const onRename = (tag: Tag) => {
    let name = tag.name;
    Modal.confirm({
      title: "重命名标签",
      content: (
        <Input
          defaultValue={tag.name}
          maxLength={64}
          onChange={(e) => {
            name = e.target.value;
          }}
        />
      ),
      onOk: () => renameMut.mutate({ id: tag.id, name: name.trim() }),
    });
  };

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      render: (name: string, tag: Tag) => (
        <AntTag color={tag.color ?? "blue"} style={{ marginInlineEnd: 0 }}>
          {name}
        </AntTag>
      ),
    },
    {
      title: "颜色",
      dataIndex: "color",
      width: 90,
      render: (color: string | null, tag: Tag) => (
        <ColorPicker
          size="small"
          value={color ?? "#1677ff"}
          onChangeComplete={(c) => colorMut.mutate({ id: tag.id, color: c.toHexString() })}
        />
      ),
    },
    {
      title: "题目数",
      dataIndex: "question_count",
      width: 80,
      sorter: (a: Tag, b: Tag) => (a.question_count ?? 0) - (b.question_count ?? 0),
      render: (v?: number) => v ?? 0,
    },
    {
      title: "操作",
      key: "act",
      width: 120,
      render: (_: unknown, tag: Tag) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => onRename(tag)}>
            重命名
          </Button>
          <Popconfirm
            title="删除该标签？"
            description={
              tag.question_count
                ? `将有 ${tag.question_count} 道题目失去此标签`
                : "该标签未被任何题目使用"
            }
            onConfirm={() => deleteMut.mutate(tag.id)}
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      size="small"
      title={`标签（${tags.length}）`}
      extra={
        <Button
          size="small"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            setOpen(true);
          }}
        >
          新建标签
        </Button>
      }
    >
      <Table<Tag>
        rowKey="id"
        size="small"
        loading={isLoading}
        scroll={{ x: 520 }}
        columns={columns}
        dataSource={tags}
        pagination={false}
        locale={{
          emptyText: <Empty description="暂无标签" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
        }}
      />

      <Modal
        title="新建标签"
        open={open}
        onOk={() => form.validateFields().then((v) => createMut.mutate(v))}
        onCancel={() => setOpen(false)}
        confirmLoading={createMut.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ color: "#1677ff" }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, whitespace: true, message: "请输入名称" }]}
          >
            <Input maxLength={64} placeholder="如：TCP、高频考点" />
          </Form.Item>
          <Form.Item
            name="color"
            label="颜色"
            getValueFromEvent={(c) => (typeof c === "string" ? c : c.toHexString())}
          >
            <ColorPicker showText format="hex" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
