import { Typography } from "antd";
import type { QuestionType } from "../../types/question";

interface Props {
  type: QuestionType | string;
  payload: Record<string, any>;
  answer: Record<string, any>;
}

/**
 * 把后端存储的 answer 字典（如 {"correct":["A","B"]}）渲染成可读文本，
 * 替代练习/错题里直接 JSON.stringify 打出的裸 JSON。
 */
export function AnswerReveal({ type, answer }: Props) {
  if (type === "single_choice") {
    // 选项文本已在题目区展示，此处只给答案键，避免重复
    const c = answer?.correct;
    return (
      <Typography.Text>
        正确答案：<b>{c}</b>
      </Typography.Text>
    );
  }

  if (type === "multiple_choice") {
    const arr: string[] = answer?.correct ?? [];
    return (
      <Typography.Text>
        正确答案：<b>{arr.join(" / ")}</b>
      </Typography.Text>
    );
  }

  if (type === "fill_blank") {
    const blanks: any[] = answer?.blanks ?? [];
    if (blanks.length === 0) return <Typography.Text>（无空）</Typography.Text>;
    return (
      <Typography.Text>
        参考答案：
        {blanks.map((b, i) => {
          const accepted: string[] = b?.accepted ?? [];
          const hint = b?.hint ? `（${b.hint}）` : "";
          return (
            <span key={i}>
              {i > 0 ? "； " : ""}空{i + 1}
              {hint}：<b>{accepted.join(" / ") || "—"}</b>
            </span>
          );
        })}
      </Typography.Text>
    );
  }

  if (type === "coding") {
    return (
      <div>
        <Typography.Text strong>参考代码：</Typography.Text>
        {answer?.reference_code ? (
          <pre className="code-block" style={{ marginTop: 6 }}>
            {answer.reference_code}
          </pre>
        ) : (
          <Typography.Text type="secondary">（无）</Typography.Text>
        )}
        {answer?.complexity ? (
          <Typography.Text type="secondary">　复杂度：{answer.complexity}</Typography.Text>
        ) : null}
      </div>
    );
  }

  if (type === "essay") {
    return (
      <div>
        <Typography.Text strong>参考答案：</Typography.Text>
        {answer?.reference_answer ? (
          <Typography.Paragraph style={{ whiteSpace: "pre-wrap", marginTop: 6, marginBottom: 0 }}>
            {answer.reference_answer}
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">（无）</Typography.Text>
        )}
        {Array.isArray(answer?.keywords) && answer.keywords.length > 0 ? (
          <Typography.Text type="secondary">　关键词：{answer.keywords.join("、")}</Typography.Text>
        ) : null}
      </div>
    );
  }

  // 兜底：未知题型仍退回原样（理论上不会走到）
  return <Typography.Text>{JSON.stringify(answer)}</Typography.Text>;
}
