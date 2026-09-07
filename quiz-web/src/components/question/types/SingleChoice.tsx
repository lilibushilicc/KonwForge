import { Button, Input, Radio, Space, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";

export interface EditProps {
  payload: Record<string, any>;
  answer: Record<string, any>;
  onChange: (patch: { payload?: any; answer?: any }) => void;
}

export interface ViewProps {
  payload: Record<string, any>;
  value?: any;
  answer?: Record<string, any>;
  mode?: "answer" | "review";
}

function keyAt(i: number) {
  return String.fromCharCode(65 + i);
}

export function SingleChoiceEditor({ payload, answer, onChange }: EditProps) {
  const options: { key: string; text: string }[] = payload.options ?? [];

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
          <Radio
            checked={answer.correct === keyAt(i)}
            onChange={() => onChange({ answer: { correct: keyAt(i) } })}
          >
            正确答案
          </Radio>
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

export function SingleChoiceView({ payload, answer, mode }: ViewProps) {
  const options: { key: string; text: string }[] = payload.options ?? [];
  return (
    <div>
      {options.map((opt) => {
        const isCorrect = answer?.correct === opt.key;
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
        <Typography.Text type="secondary">正确答案：{answer?.correct}</Typography.Text>
      )}
    </div>
  );
}
