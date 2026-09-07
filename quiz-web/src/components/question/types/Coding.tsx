import { Button, Input, Select, Space, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { EditProps, ViewProps } from "./SingleChoice";

export function CodingEditor({ payload, answer, onChange }: EditProps) {
  const language = payload.language ?? "python";
  const template: string = payload.template ?? "";
  const testcases: any[] = payload.testcases ?? [];
  const reference_code: string = answer.reference_code ?? "";
  const complexity: string = answer.complexity ?? "";

  const patchPayload = (p: Record<string, any>) => onChange({ payload: { ...payload, ...p } });
  const patchAnswer = (a: Record<string, any>) => onChange({ answer: { ...answer, ...a } });

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Space>
        <Typography.Text>语言</Typography.Text>
        <Select
          value={language}
          style={{ width: 160 }}
          onChange={(v) => patchPayload({ language: v })}
          options={[
            { value: "python", label: "Python" },
            { value: "javascript", label: "JavaScript" },
            { value: "java", label: "Java" },
            { value: "cpp", label: "C++" },
            { value: "go", label: "Go" },
          ]}
        />
        <Typography.Text>复杂度</Typography.Text>
        <Input
          value={complexity}
          style={{ width: 160 }}
          placeholder="如 O(n log n)"
          onChange={(e) => patchAnswer({ complexity: e.target.value })}
        />
      </Space>

      <div>
        <Typography.Text type="secondary">代码模板</Typography.Text>
        <Input.TextArea
          value={template}
          style={{ fontFamily: "monospace", minHeight: 120 }}
          onChange={(e) => patchPayload({ template: e.target.value })}
        />
      </div>

      <div>
        <Typography.Text type="secondary">测试用例</Typography.Text>
        {testcases.map((tc, i) => (
          <Space key={i} align="start" style={{ display: "flex", marginBottom: 8 }}>
            <Input.TextArea
              value={tc.input}
              placeholder="输入"
              autoSize={{ minRows: 1 }}
              style={{ width: 220, fontFamily: "monospace" }}
              onChange={(e) => {
                const n = testcases.slice();
                n[i] = { ...tc, input: e.target.value };
                patchPayload({ testcases: n });
              }}
            />
            <Input
              value={tc.expected}
              placeholder="期望输出"
              style={{ width: 180, fontFamily: "monospace" }}
              onChange={(e) => {
                const n = testcases.slice();
                n[i] = { ...tc, expected: e.target.value };
                patchPayload({ testcases: n });
              }}
            />
            <Typography.Text>隐藏</Typography.Text>
            <input
              type="checkbox"
              checked={!!tc.hidden}
              onChange={(e) => {
                const n = testcases.slice();
                n[i] = { ...tc, hidden: e.target.checked };
                patchPayload({ testcases: n });
              }}
            />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => patchPayload({ testcases: testcases.filter((_, j) => j !== i) })}
            />
          </Space>
        ))}
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() =>
            patchPayload({ testcases: [...testcases, { input: "", expected: "", hidden: false }] })
          }
        >
          添加用例
        </Button>
      </div>

      <div>
        <Typography.Text type="secondary">参考实现</Typography.Text>
        <Input.TextArea
          value={reference_code}
          style={{ fontFamily: "monospace", minHeight: 120 }}
          onChange={(e) => patchAnswer({ reference_code: e.target.value })}
        />
      </div>
    </Space>
  );
}

export function CodingView({ payload, answer }: ViewProps) {
  const testcases: any[] = payload.testcases ?? [];
  return (
    <div>
      <Typography.Text type="secondary">语言：{payload.language}</Typography.Text>
      {payload.template && <pre className="code-block">{payload.template}</pre>}
      <Typography.Text type="secondary">
        测试用例：{testcases.length} 个（{testcases.filter((t) => !t.hidden).length} 可见）
      </Typography.Text>
      {answer?.reference_code && (
        <>
          <div style={{ marginTop: 8 }}>参考实现：</div>
          <pre className="code-block">{answer.reference_code}</pre>
        </>
      )}
    </div>
  );
}
