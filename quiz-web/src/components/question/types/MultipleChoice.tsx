import { Button, Checkbox, Input, Space, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { EditProps, ViewProps } from "./SingleChoice";

function keyAt(i: number) {
  return String.fromCharCode(65 + i);
}

export function MultipleChoiceEditor({ payload, answer, onChange }: EditProps) {
  const options: { key: string; text: string }[] = payload.options ?? [];
  const correct: string[] = answer.correct ?? [];

  const setOptions = (next: { key: string; text: string }[]) =>
    onChange({ payload: { ...payload, options: next } });

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      {options.map((opt, i) => (
        <Space key={i} align="center">
          <Typography.Text strong>{keyAt(i)}</Typography.Text>
          <Input
            value={opt.text}
            placeholder={`选项 ${keyAt(i)} 内容`}
            style={{ width: 420 }}
            onChange={(e) => {
              const next = options.slice();
              next[i] = { ...opt, text: e.target.value };
              setOptions(next);
            }}
          />
          <Checkbox
            checked={correct.includes(keyAt(i))}
            onChange={(e) => {
              const set = new Set(correct);
              e.target.checked ? set.add(keyAt(i)) : set.delete(keyAt(i));
              onChange({ answer: { correct: [...set] } });
            }}
          >
            正确
          </Checkbox>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => setOptions(options.filter((_, j) => j !== i))}
          />
        </Space>
      ))}
      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={() => setOptions([...options, { key: keyAt(options.length), text: "" }])}
      >
        添加选项
      </Button>
    </Space>
  );
}

export function MultipleChoiceView({ payload, answer, mode }: ViewProps) {
  const options: { key: string; text: string }[] = payload.options ?? [];
  const correct: string[] = answer?.correct ?? [];
  return (
    <div>
      {options.map((opt) => {
        const isCorrect = correct.includes(opt.key);
        return (
          <div className="option-row" key={opt.key}>
            <span
              className="option-key"
              style={
                mode === "review" && isCorrect
                  ? { borderColor: "#3F8F6B", color: "#3F8F6B" }
                  : undefined
              }
            >
              {opt.key}
            </span>
            <span className="q-stem">{opt.text}</span>
          </div>
        );
      })}
      {mode === "review" && (
        <Typography.Text type="secondary">正确答案：{correct.join(" / ")}</Typography.Text>
      )}
    </div>
  );
}
