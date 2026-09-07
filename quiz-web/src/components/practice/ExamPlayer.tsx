import { useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Drawer,
  Modal,
  Progress,
  Result,
  Space,
  Typography,
  message,
} from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ProfileOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { QuestionPlayer, EssaySelfEval } from "./QuestionPlayer";
import { AnswerReveal } from "./AnswerReveal";
import { AnswerSheet, type SheetState } from "./AnswerSheet";
import {
  practiceApi,
  type AnswerSubmit,
  type PracticeSession,
  type SessionSubmitResult,
} from "../../api/practice";
import { TYPE_LABELS } from "../../stores/bankStore";

/** 判断某题是否已作答（用于进度与答题卡状态）。 */
function isAnswered(type: string, response?: Record<string, any>): boolean {
  if (!response) return false;
  switch (type) {
    case "single_choice":
      return !!response.choice;
    case "multiple_choice":
      return Array.isArray(response.choices) && response.choices.length > 0;
    case "fill_blank": {
      const b = response.blanks || {};
      return Object.values(b).some((v) => typeof v === "string" && v.trim() !== "");
    }
    case "coding":
      return typeof response.code === "string" && response.code.trim() !== "";
    case "essay":
      return typeof response.text === "string" && response.text.trim() !== "";
    default:
      return false;
  }
}

/** 窄屏检测（与移动端适配 breakpoint 一致：767px）。 */
function useIsMobile() {
  const [mobile, setMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches,
  );
  useMemo(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(max-width: 767px)");
    const handler = () => setMobile(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
}

export function ExamPlayer({ session }: { session: PracticeSession }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isMobile = useIsMobile();

  const [cur, setCur] = useState<PracticeSession>(session);
  const [responses, setResponses] = useState<
    Record<number, { response: any; self_eval?: string }>
  >({});
  const [flagged, setFlagged] = useState<Record<number, boolean>>({});
  const [review, setReview] = useState(false);
  const [summary, setSummary] = useState<SessionSubmitResult | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const refs = useRef<Record<number, HTMLDivElement | null>>({});

  const total = cur.items.length;
  const answeredCount = cur.items.filter((i) =>
    isAnswered(i.question.type, responses[i.id]?.response),
  ).length;
  const unansweredCount = total - answeredCount;

  const cells = cur.items.map((item, idx): { index: number; state: SheetState; flagged: boolean } => {
    let state: SheetState;
    if (review) {
      state =
        item.is_correct === true ? "correct" : item.is_correct === false ? "incorrect" : "unanswered";
    } else {
      state = isAnswered(item.question.type, responses[item.id]?.response) ? "answered" : "unanswered";
    }
    return { index: idx, state, flagged: !!flagged[item.id] };
  });

  const submitMut = useMutation({
    mutationFn: async () => {
      const submits: AnswerSubmit[] = cur.items
        .filter((i) => isAnswered(i.question.type, responses[i.id]?.response))
        .map((i) => ({
          item_id: i.id,
          response: responses[i.id].response,
          self_eval: (responses[i.id]?.self_eval as AnswerSubmit["self_eval"]) ?? null,
        }));
      await practiceApi.answerBatch(cur.id, submits);
      const res = await practiceApi.submit(cur.id);
      const fresh = await practiceApi.get(cur.id);
      return { res, fresh };
    },
    onSuccess: ({ res, fresh }) => {
      setCur(fresh);
      setSummary(res);
      setReview(true);
      setSheetOpen(false);
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: () => message.error("交卷失败，请重试"),
  });

  const handleSubmit = () => {
    if (unansweredCount > 0) {
      Modal.confirm({
        title: "仍有未作答题目",
        content: `还有 ${unansweredCount} 题未作答，确定交卷吗？未答题目将不计分。`,
        okText: "确定交卷",
        cancelText: "继续作答",
        onOk: () => submitMut.mutate(),
      });
    } else {
      submitMut.mutate();
    }
  };

  const jump = (index: number) => {
    const item = cur.items[index];
    if (item) refs.current[item.id]?.scrollIntoView({ behavior: "smooth", block: "start" });
    setSheetOpen(false);
  };
  const toggleFlag = (itemId: number) =>
    setFlagged((p) => ({ ...p, [itemId]: !p[itemId] }));

  if (total === 0) {
    return (
      <Card style={{ maxWidth: 520, margin: "40px auto", textAlign: "center" }}>
        <Typography.Paragraph>该筛选条件下没有可练习的题目。</Typography.Paragraph>
        <Button type="primary" onClick={() => navigate("/practice")}>
          返回
        </Button>
      </Card>
    );
  }

  return (
    <>
      {review && summary && (
        <Result
          status={summary.accuracy != null && summary.accuracy >= 60 ? "success" : "warning"}
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
      )}

      <div className="exam-bar">
        <Space size={12} wrap>
          <Typography.Text strong>整卷考试</Typography.Text>
          <Typography.Text type="secondary">
            已答 {answeredCount} / {total}
          </Typography.Text>
          <Progress
            percent={total ? Math.round((answeredCount / total) * 100) : 0}
            showInfo={false}
            style={{ width: 160 }}
          />
        </Space>
        <Space>
          <Button icon={<ProfileOutlined />} onClick={() => setSheetOpen(true)}>
            答题卡
          </Button>
          {!review && (
            <Button type="primary" loading={submitMut.isPending} onClick={handleSubmit}>
              交卷
            </Button>
          )}
        </Space>
      </div>

      <div className="exam-layout">
        <div className="exam-main">
          {cur.items.map((item, idx) => {
            const answered = isAnswered(item.question.type, responses[item.id]?.response);
            return (
              <div
                key={item.id}
                ref={(el) => {
                  refs.current[item.id] = el;
                }}
                className="exam-q"
              >
                <Card>
                  <div className="exam-q__head">
                    <Space size={6} wrap>
                      <Typography.Text strong>第 {idx + 1} 题</Typography.Text>
                      <Typography.Text type="secondary">
                        {TYPE_LABELS[item.question.type as keyof typeof TYPE_LABELS] ?? item.question.type}
                        {item.question.category_name ? ` · ${item.question.category_name}` : ""}
                      </Typography.Text>
                    </Space>
                    {!review && (
                      <Button
                        size="small"
                        type={flagged[item.id] ? "primary" : "default"}
                        onClick={() => toggleFlag(item.id)}
                      >
                        {flagged[item.id] ? "已标记" : "标记本题"}
                      </Button>
                    )}
                  </div>

                  <QuestionPlayer
                    question={item.question}
                    disabled={review}
                    onChange={(r) =>
                      setResponses((p) => ({ ...p, [item.id]: { ...p[item.id], response: r } }))
                    }
                  />

                  {!review && item.question.type === "essay" && (
                    <div style={{ marginTop: 12 }}>
                      <EssaySelfEval
                        value={responses[item.id]?.self_eval}
                        onChange={(v) =>
                          setResponses((p) => ({
                            ...p,
                            [item.id]: { ...p[item.id], self_eval: v },
                          }))
                        }
                      />
                    </div>
                  )}

                  {review && (
                    <div style={{ marginTop: 16 }}>
                      <Alert
                        type={item.is_correct ? "success" : item.is_correct === false ? "error" : "warning"}
                        icon={item.is_correct ? <CheckCircleFilled /> : <CloseCircleFilled />}
                        message={
                          item.is_correct
                            ? "回答正确"
                            : item.is_correct === false
                            ? "回答错误"
                            : "未作答"
                        }
                        description={
                          item.reveal ? (
                            <div>
                              {item.reveal.answer && (
                                <Typography.Paragraph style={{ marginBottom: 4 }}>
                                  <AnswerReveal
                                    type={item.question.type}
                                    payload={item.question.payload}
                                    answer={item.reveal.answer}
                                  />
                                </Typography.Paragraph>
                              )}
                              {item.reveal.analysis && (
                                <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>
                                  <Typography.Text strong>解析：</Typography.Text>
                                  {item.reveal.analysis}
                                </Typography.Paragraph>
                              )}
                            </div>
                          ) : undefined
                        }
                      />
                    </div>
                  )}

                  {!review && !answered && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      本题尚未作答
                    </Typography.Text>
                  )}
                </Card>
              </div>
            );
          })}
        </div>

        {!isMobile && (
          <aside className="exam-side">
            <AnswerSheet
              cells={cells}
              submitted={review}
              onJump={jump}
              onToggleFlag={(index) => toggleFlag(cur.items[index].id)}
            />
          </aside>
        )}
      </div>

      <Drawer
        title="答题卡"
        placement="right"
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        width={300}
      >
        <AnswerSheet
          cells={cells}
          submitted={review}
          onJump={jump}
          onToggleFlag={(index) => toggleFlag(cur.items[index].id)}
        />
      </Drawer>
    </>
  );
}
