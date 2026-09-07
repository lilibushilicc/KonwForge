import { Input, InputNumber, Select, Space, Typography } from "antd";
import type { EditProps, ViewProps } from "./SingleChoice";

export function EssayEditor({ payload, answer, onChange }: EditProps) {
  const reference_answer: string = answer.reference_answer ?? "";
  const keywords: string[] = answer.keywords ?? [];
  const min_chars: number = answer.min_chars ?? 0;
  const max_chars: number | undefined = payload.max_chars ?? undefined;

  const patchAnswer = (a: Record<string, any>) => onChange({ answer: { ...answer, ...a } });
  const patchPayload = (p: Record<string, any>) => onChange({ payload: { ...payload, ...p } });

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Space wrap>
        <Typography.Text>最少字数</Typography.Text>
        <InputNumber
          min={0}
          value={min_chars}
          style={{ width: 120 }}
          placeholder="不限则留空 0"
          onChange={(v) => patchAnswer({ min_chars: v ?? 0 })}
        />
        <Typography.Text>最多字数（选填）</Typography.Text>
        <InputNumber
          min={0}
          value={max_chars}
          style={{ width: 120 }}
          placeholder="不限则留空"
          onChange={(v) => patchPayload({ max_chars: v ?? null })}
        />
      </Space>

      <div>
        <Typography.Text type="secondary">参考答案</Typography.Text>
        <Input.TextArea
          value={reference_answer}
          autoSize={{ minRows: 4 }}
          placeholder="支持多段文本、要点、公式等"
          onChange={(e) => patchAnswer({ reference_answer: e.target.value })}
        />
      </div>

      <div>
        <Typography.Text type="secondary">关键词提示（选填，用于主观题要点召回）</Typography.Text>
        <Select
          mode="tags"
          style={{ width: "100%" }}
          placeholder="输入要点关键词后回车"
          value={keywords}
          onChange={(v) => patchAnswer({ keywords: v })}
          tokenSeparators={[",", "，"]}
        />
      </div>
    </Space>
  );
}

export function EssayView({ payload, answer, mode }: ViewProps) {
  const min_chars: number = answer?.min_chars ?? 0;
  const max_chars: number | undefined = payload?.max_chars ?? undefined;
  const keywords: string[] = answer?.keywords ?? [];

  const limit =
    max_chars && max_chars > 0
      ? `${min_chars} ~ ${max_chars} 字`
      : min_chars > 0
        ? `至少 ${min_chars} 字`
        : "字数不限";

  return (
    <div>
      <Typography.Text type="secondary">作答要求：{limit}</Typography.Text>
      {keywords.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <Typography.Text type="secondary">要点关键词：</Typography.Text>
          {keywords.map((k) => (
            <Typography.Text code key={k} style={{ marginRight: 6 }}>
              {k}
            </Typography.Text>
          ))}
        </div>
      )}
      {mode === "review" && answer?.reference_answer && (
        <div style={{ marginTop: 8 }}>
          <Typography.Text type="secondary">参考答案：</Typography.Text>
          <div className="q-stem" style={{ marginTop: 4 }}>
            {answer.reference_answer}
          </div>
        </div>
      )}
    </div>
  );
}
