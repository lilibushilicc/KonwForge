import { useState } from "react";
import { Checkbox, Input, Radio, Select, Space, Typography } from "antd";
import type { QuestionPlay } from "../../api/practice";

const { TextArea } = Input;

/**
 * 题干渲染：``` 围栏内的代码块切出来渲染成 <pre.code-block>（主题走 CSS 变量），
 * 其余按段落文本。代码题库的 stem 形如「题干文字\n\n```python\n...\n```」。
 */
function StemContent({ stem }: { stem: string }) {
  const segments: { kind: "text" | "code"; body: string }[] = [];
  const re = /```(\w*)\n?([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(stem))) {
    if (m.index > last) segments.push({ kind: "text", body: stem.slice(last, m.index) });
    segments.push({ kind: "code", body: m[2].replace(/\n$/, "") });
    last = m.index + m[0].length;
  }
  if (last < stem.length) segments.push({ kind: "text", body: stem.slice(last) });
  if (segments.length === 0) segments.push({ kind: "text", body: stem });

  return (
    <>
      {segments.map((s, i) =>
        s.kind === "code" ? (
          <pre key={i} className="code-block" style={{ whiteSpace: "pre-wrap", margin: "8px 0" }}>
            {s.body}
          </pre>
        ) : (
          <Typography.Paragraph
            key={i}
            strong
            style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}
          >
            {s.body.trim()}
          </Typography.Paragraph>
        ),
      )}
    </>
  );
}

/**
 * 填空题题干渲染：把占位符替换成输入框。
 *
 * 【支持的占位符格式】
 *   1. 新格式：{{1}}、{{2}}、{{3}} —— 带编号，与答案配置的空 id 一一对应，推荐使用
 *   2. 旧格式：____ —— 四个下划线，按出现顺序自动编号（兼容已录入题目）
 *
 * 【修复要点】
 *   - 以 payload.blanks 配置的空数为权威渲染依据，不再靠解析题干 ____ 数量决定空数
 *   - 先把代码块整体替换成占位符再解析，避免代码里的 ____（如 __init__）被误识别
 *   - {{id}} 优先按编号匹配答案配置；匹配不上时按顺序兜底；仍匹配不上显示红色警告
 *   - 题干里多余的、未在答案配置中声明的占位符，显示为红色警告文本，不生成输入框
 */
function FillStem({
  stem,
  blanks: blankSpecs,
  values,
  onChange,
}: {
  stem: string;
  blanks: any[];
  values: Record<number, string>;
  onChange: (id: number, v: string) => void;
}) {
  const specs = Array.isArray(blankSpecs) ? blankSpecs : [];

  // 第一步：把代码块整体替换成不可见占位符 \u0000idx\u0000，避免代码内容干扰解析
  const codeBlocks: string[] = [];
  const stemWithoutCode = stem.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push(`\`\`\`${lang}\n${code}\`\`\``);
    return `\u0000${codeBlocks.length - 1}\u0000`;
  });

  // 第二步：解析占位符。{{数字}} 直接取编号；____ 按出现顺序自动编号（从 1 开始）
  const tokens: { id: number; raw: string }[] = [];
  let autoSeq = 0;
  const parts: string[] = [];
  const tokenRe = /\{\{(\d+)\}\}|____/g;
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = tokenRe.exec(stemWithoutCode))) {
    parts.push(stemWithoutCode.slice(lastIndex, m.index));
    if (m[1] !== undefined) {
      tokens.push({ id: Number(m[1]), raw: `{{${m[1]}}}` });
    } else {
      autoSeq++;
      tokens.push({ id: autoSeq, raw: "____" });
    }
    lastIndex = m.index + m[0].length;
  }
  parts.push(stemWithoutCode.slice(lastIndex));

  // 第三步：建立答案配置映射，准备渲染
  const specById = new Map<number, any>();
  specs.forEach((s) => {
    if (s?.id != null) specById.set(Number(s.id), s);
  });
  const usedSpecs = new Set<any>(); // 记录已渲染的配置，避免顺序兜底时重复使用

  const restoreCode = (text: string) =>
    text.replace(/\u0000(\d+)\u0000/g, (_, idx) => codeBlocks[Number(idx)] ?? "");

  // 组装渲染序列：文本0 → 占位符0 → 文本1 → 占位符1 → ...
  const nodes: React.ReactNode[] = [];
  for (let i = 0; i < parts.length; i++) {
    if (parts[i]) nodes.push(<span key={`t${i}`}>{restoreCode(parts[i])}</span>);
    if (i < tokens.length) {
      const token = tokens[i];
      // 优先按编号精确匹配答案配置
      let spec = specById.get(token.id);
      // 匹配不上：按顺序找第一个未被使用的配置兜底
      if (!spec) spec = specs.find((s) => !usedSpecs.has(s)) ?? null;

      if (!spec) {
        // 该占位符未在答案配置中声明 → 红色警告，不生成输入框
        nodes.push(
          <span
            key={`b${i}`}
            style={{ color: "#ff4d4f", background: "#fff2f0", padding: "0 4px", borderRadius: 4 }}
            title={`该占位符未在填空题答案中配置（当前配置了 ${specs.length} 个空）`}
          >
            {token.raw}
          </span>,
        );
        continue;
      }
      usedSpecs.add(spec);
      const inputId = Number(spec.id ?? token.id);
      nodes.push(
        <Input
          key={`b${i}`}
          size="small"
          style={{ width: 120, display: "inline-block", margin: "0 4px" }}
          value={values[inputId] ?? ""}
          onChange={(e) => onChange(inputId, e.target.value)}
          placeholder={spec.placeholder || spec.hint || `空${inputId}`}
        />,
      );
    }
  }

  return <Typography.Paragraph>{nodes}</Typography.Paragraph>;
}

/**
 * 只读展示题目 + 作答控件。onChange 回调当前 response。
 * response 形状与后端 judge 对齐：
 *  - single_choice: { choice: "B" }
 *  - multiple_choice: { choices: ["A","B"] }
 *  - fill_blank: { blanks: { 1: "x", 2: "y" } }（按空 id）
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
        <StemContent stem={stem} />
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
        <StemContent stem={stem} />
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
            blanks={payload?.blanks ?? []}
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
        <StemContent stem={stem} />
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
      <StemContent stem={stem} />
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
