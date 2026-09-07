import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  InputNumber,
  Progress,
  Result,
  Select,
  Space,
  TreeSelect,
  Typography,
  message,
} from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  PlayCircleOutlined,
  RedoOutlined,
} from "@ant-design/icons";

import { PageHeader } from "../../components/common/PageHeader";
import { QuestionPlayer, EssaySelfEval } from "../../components/practice/QuestionPlayer";
import { AnswerReveal } from "../../components/practice/AnswerReveal";
import { ExamPlayer } from "../../components/practice/ExamPlayer";
import { practiceApi, type PracticeSession, type PracticeSessionCreate } from "../../api/practice";
import { categoriesApi } from "../../api/categories";
import type { Category } from "../../api/categories";

const TYPE_OPTIONS = [
  { value: "single_choice", label: "单选" },
  { value: "multiple_choice", label: "多选" },
  { value: "fill_blank", label: "填空" },
  { value: "coding", label: "代码" },
  { value: "essay", label: "简答" },
];
const DIFF_OPTIONS = [1, 2, 3, 4, 5].map((d) => ({ value: d, label: `难度 ${d}` }));
const MODE_OPTIONS = [
  { value: "practice", label: "顺序练习（逐题判分）" },
  { value: "category", label: "分类练习（练全部分类题）" },
  { value: "exam", label: "整卷考试（交卷后判分）" },
];

function buildTree(cats: Category[]) {
  const map = new Map<number, any>();
  cats.forEach((c) => map.set(c.id, { ...c, title: c.name, value: c.id, key: c.id, children: [] }));
  const roots: any[] = [];
  map.forEach((node) => {
    if (node.parent_id && map.has(node.parent_id)) map.get(node.parent_id).children.push(node);
    else roots.push(node);
  });
  return roots;
}

function SetupCard({ onStart }: { onStart: (cfg: PracticeSessionCreate) => void }) {
  const { data: cats = [] } = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const [mode, setMode] = useState<"practice" | "exam" | "category">("practice");
  const [count, setCount] = useState(10);
  const [types, setTypes] = useState<string[]>([]);
  const [diffs, setDiffs] = useState<number[]>([]);
  const [catIds, setCatIds] = useState<number[]>([]);

  const isCategory = mode === "category";

  const handleStart = () => {
    if (isCategory && catIds.length !== 1) {
      message.warning("请选择一个分类");
      return;
    }
    onStart({
      mode,
      count: isCategory ? 9999 : count,
      filter: {
        category_ids: catIds,
        types: isCategory ? [] : types,
        difficulties: isCategory ? [] : diffs,
      },
    });
  };

  return (
    <Card title="新建练习" className="setup-card" style={{ maxWidth: 720, margin: "0 auto" }}>
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <div>
          <Typography.Text type="secondary">模式</Typography.Text>
          <Select
            style={{ width: 260, marginLeft: 12 }}
            value={mode}
            onChange={setMode}
            options={MODE_OPTIONS}
          />
        </div>

        {isCategory ? (
          <div>
            <Typography.Text type="secondary">分类</Typography.Text>
            <TreeSelect
              style={{ width: "calc(100% - 56px)", marginLeft: 12 }}
              placeholder="选择一个分类"
              value={catIds[0]}
              onChange={(v: number | undefined) => setCatIds(v ? [v] : [])}
              treeData={buildTree(cats)}
              treeDefaultExpandAll
            />
            <Typography.Paragraph type="secondary" style={{ margin: "8px 0 0 56px", fontSize: 12 }}>
              将连续练习该分类下的全部题目（按「选择题 → 填空题 → 简答题 → 代码题」固定顺序排列）。
            </Typography.Paragraph>
          </div>
        ) : (
          <>
            <div>
              <Typography.Text type="secondary">题量</Typography.Text>
              <InputNumber
                min={1}
                max={200}
                value={count}
                onChange={(v) => setCount(v ?? 10)}
                style={{ marginLeft: 12, width: 120 }}
              />
            </div>
            <div>
              <Typography.Text type="secondary">题型</Typography.Text>
              <Select
                mode="multiple"
                allowClear
                style={{ width: "calc(100% - 56px)", marginLeft: 12 }}
                placeholder="不限"
                value={types}
                onChange={setTypes}
                options={TYPE_OPTIONS}
              />
            </div>
            <div>
              <Typography.Text type="secondary">难度</Typography.Text>
              <Select
                mode="multiple"
                allowClear
                style={{ width: "calc(100% - 56px)", marginLeft: 12 }}
                placeholder="不限"
                value={diffs}
                onChange={setDiffs}
                options={DIFF_OPTIONS}
              />
            </div>
            <div>
              <Typography.Text type="secondary">分类</Typography.Text>
              <TreeSelect
                multiple
                treeCheckable
                allowClear
                style={{ width: "calc(100% - 56px)", marginLeft: 12 }}
                placeholder="不限"
                value={catIds}
                onChange={setCatIds}
                treeData={buildTree(cats)}
                treeDefaultExpandAll
              />
            </div>
          </>
        )}

        <Button type="primary" size="large" icon={<PlayCircleOutlined />} onClick={handleStart}>
          开始练习
        </Button>
      </Space>
    </Card>
  );
}

function Player({ session }: { session: PracticeSession }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const items = session.items;
  const [idx, setIdx] = useState(0);
  const [response, setResponse] = useState<Record<string, any>>({});
  const [selfEval, setSelfEval] = useState<string>();
  const [result, setResult] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);

  const item = items[idx];
  const total = items.length;
  const answered = items.filter((i) => i.answered).length;

  const answerMut = useMutation({
    mutationFn: () =>
      practiceApi.answer(session.id, { item_id: item.id, response, self_eval: selfEval as any }),
    onSuccess: (r) => setResult(r),
    onError: () => message.error("作答失败"),
  });
  const submitMut = useMutation({
    mutationFn: () => practiceApi.submit(session.id),
    onSuccess: (s) => {
      setSummary(s);
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  if (summary) {
    return (
      <Result
        status={summary.accuracy >= 60 ? "success" : "warning"}
        title={`正确率 ${summary.accuracy ?? 0}%`}
        subTitle={`答对 ${summary.correct_count} / ${summary.total_count} 题`}
        extra={[
          <Button type="primary" key="again" onClick={() => navigate("/practice")}>
            再来一组
          </Button>,
          <Button key="mistakes" onClick={() => navigate("/mistakes")}>
            查看错题本
          </Button>,
        ]}
      />
    );
  }

  return (
    <div style={{ maxWidth: 820, margin: "0 auto" }}>
      <Progress percent={Math.round((answered / total) * 100)} showInfo={false} />
      <Typography.Text type="secondary">
        第 {idx + 1} / {total} 题 · {item.question.type}
        {item.question.category_name ? ` · ${item.question.category_name}` : ""}
      </Typography.Text>

      <Card style={{ marginTop: 12, minHeight: 280 }}>
        <QuestionPlayer question={item.question} disabled={!!result} onChange={setResponse} />

        {result && (
          <Alert
            style={{ marginTop: 16 }}
            type={result.correct ? "success" : "error"}
            icon={result.correct ? <CheckCircleFilled /> : <CloseCircleFilled />}
            message={result.correct ? "回答正确" : "回答错误"}
            description={
              <div>
                {result.reveal?.answer && (
                  <Typography.Paragraph style={{ marginBottom: 4 }}>
                    <AnswerReveal
                      type={item.question.type}
                      payload={item.question.payload}
                      answer={result.reveal.answer}
                    />
                  </Typography.Paragraph>
                )}
                {result.reveal?.analysis && (
                  <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>
                    <Typography.Text strong>解析：</Typography.Text>
                    {result.reveal.analysis}
                  </Typography.Paragraph>
                )}
              </div>
            }
          />
        )}

        {!result && item.question.type === "essay" && (
          <div style={{ marginTop: 12 }}>
            <EssaySelfEval value={selfEval} onChange={setSelfEval} />
          </div>
        )}
      </Card>

      <div style={{ marginTop: 16, display: "flex", justifyContent: "space-between" }}>
        <Button
          disabled={idx === 0}
          onClick={() => {
            setIdx(idx - 1);
            setResult(null);
            setResponse({});
          }}
        >
          上一题
        </Button>
        {!result ? (
          <Button
            type="primary"
            loading={answerMut.isPending}
            onClick={() => answerMut.mutate()}
            disabled={item.question.type === "essay" && !selfEval}
          >
            提交本题
          </Button>
        ) : idx < total - 1 ? (
          <Button
            type="primary"
            onClick={() => {
              setIdx(idx + 1);
              setResult(null);
              setResponse({});
              setSelfEval(undefined);
            }}
          >
            下一题
          </Button>
        ) : (
          <Button type="primary" loading={submitMut.isPending} onClick={() => submitMut.mutate()}>
            交卷
          </Button>
        )}
      </div>
    </div>
  );
}

export default function Practice() {
  const [params] = useSearchParams();
  const [session, setSession] = useState<PracticeSession | null>(null);
  const createMut = useMutation({
    mutationFn: (cfg: PracticeSessionCreate) => practiceApi.create(cfg),
    onSuccess: setSession,
    onError: () => message.error("创建会话失败"),
  });

  const startCreate = useMemo(
    () => (cfg: PracticeSessionCreate) => createMut.mutate(cfg),
    [createMut],
  );

  // 从错题本深链进入：?mode=mistake 直接开错题练习
  const mistakeMode = params.get("mode") === "mistake";
  if (mistakeMode && !session) {
    return (
      <Wrap>
        <MistakeStart onReady={setSession} />
      </Wrap>
    );
  }

  return (
    <Wrap>
      {session ? (
        session.mode === "exam" ? (
          <ExamPlayer session={session} />
        ) : (
          <Player session={session} />
        )
      ) : (
        <SetupCard onStart={startCreate} />
      )}
    </Wrap>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PageHeader title="练习" sub="逐题作答 · 即时判分 · 自动记录错题与掌握度" />
      {children}
    </>
  );
}

function MistakeStart({ onReady }: { onReady: (s: PracticeSession) => void }) {
  const mut = useMutation({
    mutationFn: () => practiceApi.create({ mode: "mistake", count: 20 }),
    onSuccess: onReady,
    onError: () => message.error("暂无错题可练"),
  });
  return (
    <Card style={{ maxWidth: 520, margin: "40px auto", textAlign: "center" }}>
      <Typography.Paragraph>从错题本进入：用你尚未掌握的错题生成一组练习。</Typography.Paragraph>
      <Button
        type="primary"
        loading={mut.isPending}
        icon={<RedoOutlined />}
        onClick={() => mut.mutate()}
      >
        开始错题重练
      </Button>
    </Card>
  );
}
