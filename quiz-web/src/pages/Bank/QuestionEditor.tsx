import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  TreeSelect,
  Typography,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../../components/common/PageHeader";
import { questionsApi } from "../../api/questions";
import { categoriesApi, tagsApi } from "../../api/categories";
import { getTypeMeta, QUESTION_TYPES } from "../../components/question/registry";
import { TYPE_LABELS } from "../../stores/bankStore";
import { buildCategoryTree } from "../../utils/category";
import type { QuestionDraft, QuestionType } from "../../types/question";

const { TextArea } = Input;

interface EditorState {
  type: QuestionType;
  stem: string;
  analysis: string;
  difficulty: number;
  category_id: number | null;
  tags: string[];
  source: string;
  payload: Record<string, any>;
  answer: Record<string, any>;
}

function defaultsFor(type: QuestionType): Pick<EditorState, "payload" | "answer"> {
  const meta = getTypeMeta(type);
  return { payload: meta.defaultPayload(), answer: meta.defaultAnswer() };
}

export default function QuestionEditor() {
  const { id } = useParams();
  const editing = !!id && id !== "new";
  const navigate = useNavigate();
  const { message } = App.useApp();
  const qc = useQueryClient();

  const { data: existing, isLoading } = useQuery({
    queryKey: ["question", id],
    queryFn: () => questionsApi.get(Number(id)),
    enabled: editing,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  });
  const { data: tags = [] } = useQuery({ queryKey: ["tags"], queryFn: tagsApi.list });

  const categoryTree = useMemo(() => buildCategoryTree(categories), [categories]);

  const [s, setS] = useState<EditorState>(() => ({
    type: "single_choice",
    stem: "",
    analysis: "",
    difficulty: 3,
    category_id: null,
    tags: [],
    source: "",
    ...defaultsFor("single_choice"),
  }));

  // 编辑态回填
  useEffect(() => {
    if (editing && existing) {
      setS({
        type: existing.type,
        stem: existing.stem ?? "",
        analysis: existing.analysis ?? "",
        difficulty: existing.difficulty,
        category_id: existing.category_id ?? null,
        tags: existing.tags ?? [],
        source: existing.source ?? "",
        payload: existing.payload ?? {},
        answer: existing.answer ?? {},
      });
    }
  }, [editing, existing]);

  const meta = getTypeMeta(s.type);
  const Editor = meta.Editor;

  const patch = (p: Partial<EditorState>) => setS((prev) => ({ ...prev, ...p }));

  // ---- 快捷建分类（A2）：弹窗即建即选，不打断录题 ----
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [catForm] = Form.useForm<{ name: string; parent_id?: number | null }>();
  const stemRef = useRef<HTMLTextAreaElement>(null);

  const createCatMut = useMutation({
    mutationFn: (v: { name: string; parent_id?: number | null }) =>
      categoriesApi.create({ name: v.name, parent_id: v.parent_id ?? null }),
    onSuccess: (cat) => {
      message.success(`分类「${cat.name}」已创建`);
      setCatModalOpen(false);
      catForm.resetFields();
      qc.invalidateQueries({ queryKey: ["categories"] });
      patch({ category_id: cat.id });
    },
    onError: (e: any) => message.error(e?.message ?? "创建分类失败"),
  });

  const onTypeChange = (type: QuestionType) => patch({ type, ...defaultsFor(type) });

  const saveMut = useMutation({
    mutationFn: async (_vars: { cont: boolean }) => {
      const draft: QuestionDraft = {
        type: s.type,
        stem: s.stem.trim(),
        analysis: s.analysis.trim() || null,
        difficulty: s.difficulty,
        category_id: s.category_id,
        tags: s.tags,
        payload: s.payload,
        answer: s.answer,
        judge_config: {},
        source: s.source.trim() || null,
      };
      if (editing) return questionsApi.update(Number(id), draft);
      return questionsApi.create(draft);
    },
    onSuccess: (res: any, vars) => {
      message.success(editing ? "已保存" : vars.cont ? "已保存，继续录入下一题" : "已创建");
      qc.invalidateQueries({ queryKey: ["questions"] });
      if (editing) {
        qc.invalidateQueries({ queryKey: ["question", id] });
        navigate(`/bank/${res.id}/edit`);
        return;
      }
      if (vars.cont) {
        // 连续录入：保留题型/难度/分类/标签/来源，只清题干/解析/答案/题目设置
        setS((prev) => ({
          ...prev,
          stem: "",
          analysis: "",
          payload: getTypeMeta(prev.type).defaultPayload(),
          answer: getTypeMeta(prev.type).defaultAnswer(),
        }));
        stemRef.current?.focus();
      } else {
        navigate(`/bank/${res.id}/edit`);
      }
    },
    onError: (e: any) => message.error(e?.message ?? "保存失败"),
  });

  const onSave = (cont = false) => {
    if (!s.stem.trim()) {
      message.warning("请填写题干");
      return;
    }
    saveMut.mutate({ cont });
  };

  return (
    <>
      <PageHeader
        title={editing ? "编辑题目" : "新建题目"}
        sub={
          editing && existing
            ? `编号 ${existing.code} · v${existing.version}`
            : "选择题型后填写题干与答案"
        }
        extra={
          <Space>
            <Button onClick={() => navigate("/bank")}>返回题库</Button>
            {editing ? (
              <Button type="primary" loading={saveMut.isPending} onClick={() => onSave()}>
                保存
              </Button>
            ) : (
              <>
                <Button loading={saveMut.isPending} onClick={() => onSave()}>
                  保存
                </Button>
                <Button type="primary" loading={saveMut.isPending} onClick={() => onSave(true)}>
                  保存并继续录入
                </Button>
              </>
            )}
          </Space>
        }
      />

      {isLoading && editing ? (
        <Card>加载中…</Card>
      ) : (
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Card size="small" title="基本信息">
            <Form
              className="editor-form"
              labelCol={{ flex: "80px" }}
              wrapperCol={{ flex: "auto" }}
              labelAlign="left"
            >
              <Form.Item label="题型">
                <Select
                  style={{ width: 160 }}
                  value={s.type}
                  options={QUESTION_TYPES.map((m) => ({
                    value: m.type,
                    label: TYPE_LABELS[m.type],
                  }))}
                  onChange={onTypeChange}
                />
              </Form.Item>
              <Form.Item label="题干" required>
                <TextArea
                  ref={stemRef}
                  autoSize={{ minRows: 2 }}
                  value={s.stem}
                  placeholder="题干文本，可多行"
                  onChange={(e) => patch({ stem: e.target.value })}
                />
              </Form.Item>
              <Form.Item label="难度">
                <InputNumber
                  min={1}
                  max={5}
                  value={s.difficulty}
                  onChange={(v) => patch({ difficulty: v ?? 3 })}
                />
              </Form.Item>
              <Form.Item label="分类">
                <Space.Compact style={{ width: 300 }}>
                  <TreeSelect
                    allowClear
                    style={{ width: 260 }}
                    treeData={categoryTree}
                    treeDefaultExpandAll
                    placeholder="未分类"
                    value={s.category_id}
                    onChange={(v) => patch({ category_id: v ?? null })}
                  />
                  <Button
                    icon={<PlusOutlined />}
                    title="新建分类"
                    onClick={() => {
                      catForm.setFieldsValue({ name: "", parent_id: s.category_id ?? null });
                      setCatModalOpen(true);
                    }}
                  />
                </Space.Compact>
              </Form.Item>
              <Form.Item label="标签">
                <Select
                  mode="tags"
                  style={{ width: "100%" }}
                  tokenSeparators={[",", "，"]}
                  placeholder="输入或选择标签"
                  value={s.tags}
                  options={tags.map((t) => ({ value: t.name, label: t.name }))}
                  onChange={(v: string[]) => patch({ tags: v })}
                />
              </Form.Item>
              <Form.Item label="来源">
                <Input
                  style={{ width: 260 }}
                  placeholder="如《算法导论》P.12"
                  value={s.source}
                  onChange={(e) => patch({ source: e.target.value })}
                />
              </Form.Item>
              <Form.Item label="解析">
                <TextArea
                  autoSize={{ minRows: 2 }}
                  value={s.analysis}
                  placeholder="解题思路、要点说明（选填）"
                  onChange={(e) => patch({ analysis: e.target.value })}
                />
              </Form.Item>
            </Form>
          </Card>

          <Card
            size="small"
            title={
              <Space>
                <meta.icon />
                <span>{TYPE_LABELS[s.type]} · 题目设置与答案</span>
              </Space>
            }
          >
            {s.type !== existing?.type && editing && (
              <Alert
                style={{ marginBottom: 12 }}
                type="warning"
                showIcon
                message="切换题型将重置题目设置与答案，保存后生效"
              />
            )}
            <Editor
              payload={s.payload}
              answer={s.answer}
              onChange={(next: { payload?: any; answer?: any }) =>
                patch({
                  payload: next.payload ?? s.payload,
                  answer: next.answer ?? s.answer,
                })
              }
            />
          </Card>

          {editing && existing?.stat && (
            <Card size="small" title="练习统计">
              <Space size="large">
                <Typography.Text>作答 {existing.stat.attempt_count} 次</Typography.Text>
                <Typography.Text>错题 {existing.stat.wrong_count} 次</Typography.Text>
                <Typography.Text>掌握度 L{existing.stat.mastery}</Typography.Text>
                <Typography.Text>连胜 {existing.stat.streak}</Typography.Text>
              </Space>
            </Card>
          )}
        </Space>
      )}

      <Modal
        title="新建分类"
        open={catModalOpen}
        onOk={() => catForm.validateFields().then((v) => createCatMut.mutate(v))}
        onCancel={() => setCatModalOpen(false)}
        confirmLoading={createCatMut.isPending}
        destroyOnClose
      >
        <Form form={catForm} layout="vertical">
          <Form.Item name="parent_id" label="上级分类（留空为根分类）">
            <TreeSelect
              allowClear
              treeData={categoryTree}
              treeDefaultExpandAll
              placeholder="根分类"
            />
          </Form.Item>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, whitespace: true, message: "请输入分类名称" }]}
          >
            <Input
              maxLength={64}
              placeholder="如：计算机网络 / TCP"
              onPressEnter={() => catForm.validateFields().then((v) => createCatMut.mutate(v))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
