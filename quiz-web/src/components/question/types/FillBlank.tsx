import { Button, Input, Space, Switch, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { EditProps, ViewProps } from "./SingleChoice";

interface BlankRow {
  hint: string;
  accepted: string; // 一行一个可接受答案
  regex: string;
  case_sensitive: boolean;
  numeric_tolerance: string;
}

function read(payload: Record<string, any>, answer: Record<string, any>): BlankRow[] {
  const p: any[] = payload.blanks ?? [];
  const a: any[] = answer.blanks ?? [];
  const n = Math.max(p.length, a.length, 1);
  return Array.from({ length: n }, (_, i) => ({
    hint: p[i]?.hint ?? "",
    accepted: (a[i]?.accepted ?? []).join("\n"),
    regex: a[i]?.regex ?? "",
    case_sensitive: !!a[i]?.case_sensitive,
    numeric_tolerance: a[i]?.numeric_tolerance ?? "",
  }));
}

export function FillBlankEditor({ payload, answer, onChange }: EditProps) {
  const rows = read(payload, answer);

  const emit = (next: BlankRow[]) => {
    onChange({
      payload: {
        ...payload,
        blanks: next.map((b, i) => ({ id: i + 1, hint: b.hint, placeholder: "" })),
      },
      answer: {
        ...answer,
        blanks: next.map((b, i) => ({
          id: i + 1,
          accepted: b.accepted
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          regex: b.regex || null,
          case_sensitive: b.case_sensitive,
          numeric_tolerance: b.numeric_tolerance ? Number(b.numeric_tolerance) : 0.001,
        })),
      },
    });
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      {rows.map((r, i) => (
        <div key={i} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
          <Typography.Text type="secondary">空 {i + 1}</Typography.Text>
          <Space direction="vertical" style={{ width: "100%" }}>
            <Input
              addonBefore="提示"
              value={r.hint}
              placeholder="选填，作答时显示"
              onChange={(e) => {
                const n = rows.slice();
                n[i] = { ...r, hint: e.target.value };
                emit(n);
              }}
            />
            <Input.TextArea
              value={r.accepted}
              placeholder="可接受答案，每行一个；支持多解"
              autoSize={{ minRows: 2 }}
              onChange={(e) => {
                const n = rows.slice();
                n[i] = { ...r, accepted: e.target.value };
                emit(n);
              }}
            />
            <Space wrap>
              <Switch
                size="small"
                checked={r.case_sensitive}
                onChange={(v) => {
                  const n = rows.slice();
                  n[i] = { ...r, case_sensitive: v };
                  emit(n);
                }}
              />
              <Typography.Text>区分大小写</Typography.Text>
              <Input
                addonBefore="正则"
                value={r.regex}
                placeholder="可选，如 ^\d+$"
                style={{ width: 220 }}
                onChange={(e) => {
                  const n = rows.slice();
                  n[i] = { ...r, regex: e.target.value };
                  emit(n);
                }}
              />
              <Input
                addonBefore="数值容差"
                type="number"
                value={r.numeric_tolerance}
                style={{ width: 160 }}
                onChange={(e) => {
                  const n = rows.slice();
                  n[i] = { ...r, numeric_tolerance: e.target.value };
                  emit(n);
                }}
              />
            </Space>
          </Space>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            style={{ marginTop: 8 }}
            onClick={() => emit(rows.filter((_, j) => j !== i))}
          >
            删除空
          </Button>
        </div>
      ))}
      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={() =>
          emit([
            ...rows,
            { hint: "", accepted: "", regex: "", case_sensitive: false, numeric_tolerance: "" },
          ])
        }
      >
        添加填空
      </Button>
    </Space>
  );
}

export function FillBlankView({ payload, answer, mode }: ViewProps) {
  const blanks: any[] = answer?.blanks ?? payload?.blanks ?? [];
  return (
    <div>
      {blanks.map((b, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <Typography.Text>空 {i + 1}：</Typography.Text>
          {mode === "review" ? (
            <Typography.Text code>{(b.accepted ?? []).join(" / ")}</Typography.Text>
          ) : (
            <Typography.Text type="secondary">（待填）</Typography.Text>
          )}
        </div>
      ))}
    </div>
  );
}
