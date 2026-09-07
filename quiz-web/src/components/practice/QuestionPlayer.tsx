import { useState } from "react";
import { Checkbox, Input, Radio, Select, Space, Typography } from "antd";
import type { QuestionPlay } from "../../api/practice";

const { TextArea } = Input;

/** 题干里的 ____ 占位替换成受控输入框（按出现顺序编号）。 */
function FillStem({
  stem,
  values,
  onChange,
}: {
  stem: string;
  values: Record<number, string>;
  onChange: (id: number, v: string) => void;
}) {
  const parts = stem.split("____");
  const blanks = parts.length - 1;
  return (
    <Typography.Paragraph>
      {parts.map((p, i) => (
        <span key={i}>
          {p}
          {i < blanks && (
            <Input
              size="small"
              style={{ width: 120, display: "inline-block", margin: "0 4px" }}
              value={values[i + 1] ?? ""}
              onChange={(e) => onChange(i + 1, e.target.value)}
              placeholder={`空${i + 1}`}
            />
          )}
        </span>
      ))}
    </Typography.Paragraph>
  );
}

/**
 * 只读展示题目 + 作答控件。onChange 回调当前 response。
 * response 形状与后端 judge 对齐：
 *  - single_choice: { choice: "B" }
 *  - multiple_choice: { choices: ["A","B"] }
 *  - fill_blank: { blanks: { 1: "x", 2: "y" } }（按位置）
 *  - coding: { code: "..." }
 *  - essay: { text: "..." }
 */
export function QuestionPlayer({
  question,
  disabled,
  onChange,
}: {
  question: QuestionPlay;
  disabled?: boolean;
  onChange: (response: Record<string, any>) => void;
}) {
  const { type, stem, payload } = question;
  const [choice, setChoice] = useState<string>();
  const [choices, setChoices] = useState<string[]>([]);
  const [blanks, setBlanks] = useState<Record<number, string>>({});
  const [code, setCode] = useState("");
  const [text, setText] = useState("");

  const emit = (r: Record<string, any>) => onChange(r);

  if (type === "single_choice") {
    const options = payload?.options ?? [];
    return (
      <>
        <Typography.Paragraph strong>{stem}</Typography.Paragraph>
        <Radio.Group
          disabled={disabled}
          value={choice}
          onChange={(e) => {
            setChoice(e.target.value);
            emit({ choice: e.target.value });
          }}
        >
          <Space direction="vertical">
            {options.map((o: any) => (
              <Radio key={o.key} value={o.key}>
                {o.key}. {o.text}
              </Radio>
            ))}
          </Space>
        </Radio.Group>
      </>
    );
  }

  if (type === "multiple_choice") {
    const options = payload?.options ?? [];
    return (
      <>
        <Typography.Paragraph strong>{stem}</Typography.Paragraph>
        <Checkbox.Group
          disabled={disabled}
          value={choices}
          onChange={(vals) => {
            setChoices(vals as string[]);
            emit({ choices: vals });
          }}
        >
          <Space direction="vertical">
            {options.map((o: any) => (
              <Checkbox key={o.key} value={o.key}>
                {o.key}. {o.text}
              </Checkbox>
            ))}
          </Space>
        </Checkbox.Group>
      </>
    );
  }

  if (type === "fill_blank") {
    return (
      <>
        <Typography.Paragraph strong>
          <FillStem
            stem={stem}
            values={blanks}
            onChange={(id, v) => {
              const next = { ...blanks, [id]: v };
              setBlanks(next);
              emit({ blanks: next });
            }}
          />
        </Typography.Paragraph>
      </>
    );
  }

  if (type === "coding") {
    const template = payload?.template as string | undefined;
    return (
      <>
        <Typography.Paragraph strong>{stem}</Typography.Paragraph>
        {template && (
          <pre className="code-block" style={{ whiteSpace: "pre-wrap" }}>
            {template}
          </pre>
        )}
        <Typography.Text type="secondary">在此编写你的实现：</Typography.Text>
        <TextArea
          disabled={disabled}
          rows={6}
          style={{ fontFamily: "monospace", marginTop: 8 }}
          value={code}
          onChange={(e) => {
            setCode(e.target.value);
            emit({ code: e.target.value });
          }}
          placeholder="def solution(...):"
        />
      </>
    );
  }

  // essay
  return (
    <>
      <Typography.Paragraph strong>{stem}</Typography.Paragraph>
      <TextArea
        disabled={disabled}
        rows={5}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          emit({ text: e.target.value });
        }}
        placeholder="写下你的作答要点…"
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
        客观题由系统即时判分；简答题请作答后自评掌握程度。
      </Typography.Paragraph>
    </>
  );
}

/** 简答自评下拉（仅在提交简答作答时用到）。 */
export function EssaySelfEval({
  value,
  onChange,
}: {
  value?: string;
  onChange: (v: string) => void;
}) {
  return (
    <Select
      style={{ width: 200 }}
      placeholder="自评掌握程度"
      value={value}
      onChange={onChange}
      options={[
        { value: "mastered", label: "已掌握" },
        { value: "fuzzy", label: "模糊" },
        { value: "unknown", label: "不会" },
      ]}
    />
  );
}
